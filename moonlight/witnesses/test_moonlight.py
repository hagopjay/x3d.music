"""Moonlight witnesses that need no LMMS and no browser.

    python3 -I -m pytest -q moonlight/witnesses

Score    every event in the three event lists becomes a piano note, at the right tick and key
Project  the LMMS XML is format 31 (MIDI-numbered keys), routes, automates and stays in range
Scene    the X3D has one note box per note, one lane per instrument track, and the named nodes the page drives
Clock    the tempo map read from the project puts the Presto downbeat where the master has it (42.17 s, measured)
Kern     (when the source is reachable) re-extracting the pinned kern files gives the committed event lists
"""
import hashlib, json, os, subprocess, sys, tempfile, urllib.request
import xml.etree.ElementTree as ET
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
POC = os.path.dirname(HERE)
SCORE = os.path.join(POC, "score")
TPQ = 48


@pytest.fixture(scope="module")
def built():
    d = tempfile.mkdtemp()
    mmp = os.path.join(d, "m.mmp")
    env = dict(os.environ, TRIMS=os.path.join(POC, "lmms", "trims.json"))
    subprocess.run([sys.executable, "-I", os.path.join(POC, "lmms", "build_project.py"),
                    os.path.join(SCORE, "adagio.events.json"), os.path.join(SCORE, "presto-1-64.events.json"),
                    os.path.join(SCORE, "presto-191-201.events.json"), mmp],
                   check=True, env=env, stdout=subprocess.DEVNULL)
    from lxml import etree
    x3d = str(etree.XSLT(etree.parse(os.path.join(POC, "viz", "mmp2x3d.xsl")))(etree.parse(mmp)))
    return ET.parse(mmp).getroot(), ET.fromstring(x3d), mmp


def events(name):
    o = json.load(open(os.path.join(SCORE, name)))
    return [e for h in ("LH", "RH") for e in o[h] if e["d"] > 0]


def piano_notes(root):
    tr = [t for t in root.iter("track") if t.get("name", "").startswith("Piano")][0]
    out = []
    for c in tr.findall("midiclip"):
        p = int(c.get("pos"))
        out += [(p + int(n.get("pos")), int(n.get("key"))) for n in c.findall("note")]
    return sorted(out)


def test_score_every_event_is_a_piano_note(built):
    root, _, _ = built
    want = []
    for e in events("adagio.events.json"):
        want.append((round(e["t"] * 3 * TPQ), e["m"]))                      # Adagio at 3x note values
    for e in events("presto-1-64.events.json"):
        want.append((round((116 + e["t"]) * TPQ), e["m"]))
    for e in events("presto-191-201.events.json"):
        want.append((round((372 + e["t"]) * TPQ), e["m"]))
    assert piano_notes(root) == sorted(want)


def test_project_format_and_ranges(built):
    root, _, _ = built
    assert root.get("version") == "31", "older versions shift every key up an octave on load"
    keys = [int(n.get("key")) for n in root.iter("note")]
    assert len(keys) == 4932 and 21 <= min(keys) and max(keys) <= 108
    assert all(1 <= int(n.get("vol")) <= 200 for n in root.iter("note"))
    ids = {e.get("id") for e in root.iter() if e.get("id")}
    for ac in root.iter("automationclip"):
        assert ac.find("object").get("id") in ids, ac.get("name")
    chans = {int(c.get("num")) for c in root.iter("mixerchannel")}
    for it in root.iter("instrumenttrack"):
        assert int(it.get("mixch")) in chans
    lim = [e for e in root.find("song/mixer/mixerchannel[@num='0']").iter("CompressorControls") if e.get("limiter") == "1"]
    assert lim and lim[0].get("peakmode") == "1", "an RMS-detecting limiter lets transients through"


def test_scene_matches_project(built):
    root, x3d, _ = built
    itracks = [t for t in root.find("song/trackcontainer") if t.get("type") == "0"]
    nnotes = sum(len(t.findall("midiclip/note")) for t in itracks)
    scene = x3d.find("Scene")
    lanes = [g for g in scene.iter("Group") if (g.get("DEF") or "").startswith("LANE_")]
    assert len(lanes) == len(itracks)
    boxes = sum(len(g.findall("Transform")) - 1 for g in lanes)            # minus each lane's rail
    assert boxes == nnotes
    defs = {e.get("DEF") for e in scene.iter() if e.get("DEF")}
    assert {"PLAYHEAD", "FOLLOW_RIG", "VP_FOLLOW", "VP_OVERVIEW", "UNIT"} <= defs
    assert {f"MAT_{i}" for i in range(len(itracks))} <= defs
    assert len([b for b in scene.iter("Box") if b.get("DEF")]) == 1, "one shared geometry, USEd everywhere"


def test_clock_puts_the_presto_where_the_master_has_it(built):
    root, _, _ = built
    bid = root.find("head/bpm").get("id")
    ac = [a for a in root.iter("automationclip") if a.find("object").get("id") == bid][0]
    base = int(ac.get("pos"))
    pts = sorted((base + int(t.get("pos")), float(t.get("value"))) for t in ac.findall("time"))

    def bpm(tk):
        for (a, va), (b, vb) in zip(pts, pts[1:]):
            if a <= tk < b:
                return va + (vb - va) * (tk - a) / (b - a)
        return pts[-1][1] if tk >= pts[-1][0] else pts[0][1]
    s = sum(60 / (bpm(t) * TPQ) for t in range(116 * TPQ))
    assert abs(s - 42.17) < 0.05, s                                           # measured onset in the v1 master


def test_kern_reextract_matches(tmp_path):
    pytest.importorskip("music21")
    src = json.load(open(os.path.join(SCORE, "sources.json")))
    raw = "https://raw.githubusercontent.com/craigsapp/beethoven-piano-sonatas/" + src["commit"] + "/"
    paths = {}
    try:
        for f, want in src["files"].items():
            b = urllib.request.urlopen(raw + f, timeout=30).read()
            assert hashlib.sha256(b).hexdigest() == want, f
            p = tmp_path / os.path.basename(f); p.write_bytes(b); paths[f] = str(p)
    except OSError as e:
        pytest.skip(f"source not reachable: {e}")
    sys.path.insert(0, SCORE)
    from extract import load
    for out, ex in src["excerpts"].items():
        got = load(paths[ex["file"]], *ex["bars"])
        assert json.loads(json.dumps(got)) == json.load(open(os.path.join(SCORE, out))), out
