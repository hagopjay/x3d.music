#!/usr/bin/env python3
"""Build the page: build/page/ holds every file the browser asks for, laid out the way the host serves them.

    python3 -I page/build_page.py [--no-audio | --audio-only] [--out DIR]

  index.html            the template with the config filled in (the host wraps it in its own skeleton)
  clock.js driver.js ui.js hover.js report.js boot.js      the page's own scripts (no modules, no eval)
  xite/                 X_ITE 16.5.1 as the page's own files (never a CDN at run time)
  worlds/<piece>.x3d    the generated worlds, DOCTYPE line removed (they publish as application/xml)
  data/<piece>.json     what the page needs from the score card: bars, tempo, sections, chords, a slim table of notes by card index, hover tables, the Ode's lines
  audio/<piece>.mp4     AAC, encoded from the master WAV when it is present (the masters are not committed)
  manifest.json         every file, its size and sha256: the set the Host witness lets the server serve

The note index everywhere (world tables, pins, holes, hover) is the index into the card's `notes` array; data/<piece>.json keeps the same order.
"""
import hashlib, json, os, re, shutil, subprocess, sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "gen"))
import worldlib as W            # noqa: E402

OUT = os.path.join(ROOT, "build", "page")
WORLDS = os.path.join(ROOT, "build", "worlds")

DE = ["Freude, schöner Götterfunken,", "Tochter aus Elysium,", "Wir betreten feuertrunken,", "Himmlische, dein Heiligtum!",
      "Deine Zauber binden wieder,", "Was die Mode streng geteilt;", "Alle Menschen werden Brüder,", "Wo dein sanfter Flügel weilt."]
EN = ["Joy, beautiful spark of the gods,", "daughter of Elysium,", "drunk with fire we enter,", "heavenly one, your sanctuary.",
      "Your magic binds again", "what custom has strictly divided;", "all people become brothers", "where your gentle wing rests."]
# which stanza line (0 to 7) sits on each four-bar phrase of a statement: a reading aid laid by phrase, not Beethoven's own underlay (he repeats and reorders words)
LINES = {"S1": [0, 1, 2, 3], "S2": [4, 5, 6, 7], "S3": [0, 1, 2, 3, 6, 7], "S4": [4, 5, 6, 7, 0, 1], "Coda": [6, 7]}

PIECES = [
    dict(id="ode", n=1, title="Ode to Joy", by="Ludwig van Beethoven", camScale=4.0, credits=[
        "Melody: Beethoven, Symphony No. 9, finale (1824), public domain. Words: Friedrich Schiller, An die Freude (1785), public domain. The English gloss is ours.",
        "Score card, arrangement, synthesised sound, worlds and page: Loomsong, MIT licence. Nothing in the sound is sampled."]),
    dict(id="turca", n=2, title="Rondo alla Turca", by="Wolfgang Amadeus Mozart", camScale=1.6, credits=[
        "Mozart, Piano Sonata in A major, K. 331, third movement (1783), public domain. Encoding: Craig Stuart Sapp, Alte Mozart-Ausgabe (1878), CC BY-NC-SA 4.0, https://github.com/craigsapp/mozart-piano-sonatas.",
        "Piano: Salamander Grand Piano V3 by Alexander Holm (remapped by kinwie), CC BY 3.0. Every other voice is synthesised in code; this is not a recording of anyone playing the piece.",
        "Score card, arrangement, worlds and page: Loomsong; everything derived from the score card is shared under CC BY-NC-SA 4.0."]),
]


def strip_doctype(text):
    return re.sub(r"<!DOCTYPE[^>]*>\s*", "", text, count=1)


def lyrics(card):
    out = []
    for p in card.passes:
        lines = LINES.get(p["id"])
        if not lines:
            continue
        b0, b1 = p["bars"]
        for k, ln in enumerate(lines):
            lo = b0 + 4 * k
            if lo > b1:
                break
            hi = min(b1 + 1, lo + 4)
            t0 = card.q_t(card.bar_q(lo))
            t1 = card.seconds if hi > b1 and p["id"] == "Coda" else card.q_t(card.bar_q(hi))
            out.append(dict(t0=round(t0, 4), t1=round(t1, 4), de=DE[ln], en=EN[ln]))
    return out


def meta(piece):
    card = W.Card(piece)
    c = card.c
    inst = [i["id"] for i in c["instruments"]]
    ix = {k: i for i, k in enumerate(inst)}
    tempo = [[float(Fr(e["q"])), float(e["qpm"])] for e in c["tempo_map"]]
    probe = [round(t, 3) for t in (0.0, 1.0, 5.5, card.seconds * 0.25, card.seconds * 0.5, card.seconds * 0.75, card.seconds - 0.1, card.seconds)]
    m = dict(piece=piece, title=c["title"], D=card.D, seconds=card.seconds, beats=card.beats, pickup=card.pickup, tempo=tempo,
             bar_t=[round(d["t"], 4) for d in card.downbeats()],
             passes=[dict(id=p["id"], rep=p["rep"], label=p["label"], t0=round(p["t0"], 4), t1=round(p["t1"], 4), bars=p["bars"]) for p in card.passes],
             harmony=[[round(h["t"], 4), round(h["dur"], 4), h["key"], h["roman"], h["root"], h["qual"], h["tension"]] for h in c["harmony"]],
             inst=inst,
             notes=[[ix[n["inst"]], n["pitch"], n["vel"], round(n["t"], 4), round(n["dur"], 4), n["bar"], n["beat"], 0 if n["layer"] == "composer" else 1] for n in card.notes],
             ids=[n["id"] for n in card.notes],
             qcheck=[[t, card.t_q(t)] for t in probe])
    if piece == "ode":
        m["lyrics"] = lyrics(card)
    with open(os.path.join(WORLDS, piece + ".map.json"), encoding="utf-8") as f:
        mp = json.load(f)
    m["map"] = {k: v for k, v in mp.items() if k not in ("holes",)}                # holes is the identity (hole i is note i); the rest is what hover reads
    return m


def encode_audio(piece, enabled=True):
    wav = os.path.join(ROOT, "build", "audio", piece, piece + ".master.wav")
    out = os.path.join(OUT, "audio", piece + ".mp4")
    if not enabled or not os.path.exists(wav):
        return os.path.exists(out)                      # an earlier build's file stays in the set
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(wav):
        return True
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)
    return True


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv):
    global OUT
    if "--out" in argv:                                # a second build somewhere else (the private preview is built with the host's object name; build/page stays the form CI tests)
        OUT = os.path.abspath(argv[argv.index("--out") + 1])
    audio = "--no-audio" not in argv
    os.makedirs(OUT, exist_ok=True)
    if "--audio-only" in argv:                         # CI's audio job: encode the masters it has just rendered and stop; the page job downloads the .mp4 files
        for p in PIECES:
            print("audio %s: %s" % (p["id"], "encoded" if encode_audio(p["id"], True) else "no master to encode"))
        return 0
    for sub in ("worlds", "data", "audio"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    cfg = dict(title="Loomsong", pieces=[])
    # The name of the host's runtime object (the page's own store lives behind it) is not written in the source: the build is given it, for the private preview only. Without it the report is off.
    cfg["hostApi"] = os.environ.get("LOOM_HOST_API", "")
    if cfg["hostApi"] and not re.fullmatch(r"[A-Za-z_$][\w$]*", cfg["hostApi"]):
        sys.exit("LOOM_HOST_API must be a plain identifier")
    have_audio = {}
    for p in PIECES:
        pid = p["id"]
        text = open(os.path.join(WORLDS, pid + ".x3d"), encoding="utf-8").read()
        with open(os.path.join(OUT, "worlds", pid + ".x3d"), "w", encoding="utf-8", newline="\n") as f:
            f.write(strip_doctype(text))
        rep = json.load(open(os.path.join(WORLDS, pid + ".report.json")))
        shaders = re.findall(r"<ComposedShader[^>]*DEF='([^']+)'", text)
        m = meta(pid)
        with open(os.path.join(OUT, "data", pid + ".json"), "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(m, separators=(",", ":"), ensure_ascii=False) + "\n")
        have_audio[pid] = encode_audio(pid, audio)
        cfg["pieces"].append(dict(id=pid, n=p["n"], title=p["title"], by=p["by"], world="worlds/%s.x3d" % pid, audio="audio/%s.mp4" % pid, meta="data/%s.json" % pid,
                                  D=rep["D"], shaders=shaders, camScale=p["camScale"], credits=p["credits"], ai=[]))
    for name in ("clock.js", "driver.js", "ui.js", "hover.js", "report.js", "boot.js"):
        shutil.copyfile(os.path.join(HERE, name), os.path.join(OUT, name))
    tpl = open(os.path.join(HERE, "index.tpl.html"), encoding="utf-8").read()
    cfg_json = json.dumps(cfg, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(tpl.replace("{{CFG}}", cfg_json))
    xite_src, xite_dst = os.path.join(ROOT, "build", "xite"), os.path.join(OUT, "xite")
    if not os.path.isdir(xite_src):
        sys.exit("build/xite is missing: run python3 -I tools/fetch_xite.py")
    if not os.path.isdir(xite_dst):
        shutil.copytree(xite_src, xite_dst)
    files = []
    for dp, _, fs in os.walk(OUT):
        for fn in sorted(fs):
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, OUT).replace(os.sep, "/")
            if rel != "manifest.json":
                files.append(dict(path=rel, bytes=os.path.getsize(full), sha256=sha(full)))
    files.sort(key=lambda x: x["path"])
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(files=files, audio=have_audio, total_bytes=sum(x["bytes"] for x in files)), f, indent=1)
    print("page: %d files, %.1f MB; audio %s; report %s" % (len(files), sum(x["bytes"] for x in files) / 1e6, have_audio, "on, host object named in the config" if cfg["hostApi"] else "off (LOOM_HOST_API not set)"))
    for x in files:
        if not x["path"].startswith("xite/"):
            print("  %-22s %9d" % (x["path"], x["bytes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
