#!/usr/bin/env python3
"""The Ode to Joy score card (composer layer, form map, authored harmony, tempo map with the coda ritardando) from sources/ode-theme.musicxml. Stdlib only.

The melody is Beethoven's (public domain), hand-encoded as MusicXML; the card plays it in the shape of the spec's arrangement table: an 8-bar intro with no melody, statements of
16, 16, 24 and 24 bars (the 24-bar form repeats bars 9 to 16), and an 8-bar coda whose first four bars quote the last phrase. Harmony is ours (D and A, with G for colour) and is
written out below bar by bar. The melody is stored at written pitch; `oct` says how many octaves away from the written pitch the arrangement sounds it.
"""
import os, sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harmony as H                                # noqa: E402
from cardlib import SCHEMA, TempoMap, dump_card, frac, metric, rnd, sha256_file   # noqa: E402

PIECE = "ode"
INST = "mel"
VOICE = "M"
STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
KEY = "D"
BAR_Q = 4

# The plan: (id, label, bars, source ranges in written quarters, octave shift of the melody for the arrangement, velocity)
STATEMENT_16 = [(Fr(0), Fr(64))]
STATEMENT_24 = [(Fr(0), Fr(64)), (Fr(32), Fr(64))]           # bars 1 to 16, then bars 9 to 16 again
PLAN = [("Intro", "the loom wakes: drone, heartbeat kick, clatter; no melody", 8, [], 0, 0),
        ("S1", "statement 1, theme alone in the bass register: one indigo thread", 16, STATEMENT_16, -2, 62),
        ("S2", "statement 2, theme in the tenor with a counter-line: a silver thread joins", 16, STATEMENT_16, -1, 72),
        ("S3", "statement 3, theme in violins and lead synth: gold arrives", 24, STATEMENT_24, 0, 86),
        ("S4", "statement 4, tutti: every colour, the tapestry completes", 24, STATEMENT_24, 0, 100),
        ("Coda", "final cadence, broadening ritardando into one big hit", 8, [(Fr(48), Fr(64))], 0, 96)]
RIT_FROM_BAR, RIT_RATIO = 89, 2                                   # the coda slows to half speed by its last quarter (integer qpm each quarter, so the map is exact)
QPM0 = 116

# Authored harmony for one 16-bar statement: bar -> [(beat offset in quarters, chord)] ; chord = (root pitch class, quality). D = 2, A = 9, G = 7.
D_, A_, G_ = (2, "M"), (9, "M"), (7, "M")
HARM = {1: [(0, D_)], 2: [(0, D_), (2, A_)], 3: [(0, D_)], 4: [(0, D_), (2, A_)], 5: [(0, D_)], 6: [(0, D_), (2, A_)], 7: [(0, D_)], 8: [(0, A_), (2, D_)],
        9: [(0, A_), (2, D_)], 10: [(0, A_), (2, D_)], 11: [(0, A_), (1, G_), (3, A_)], 12: [(0, D_), (2, A_)], 13: [(0, D_)], 14: [(0, D_), (2, A_)], 15: [(0, D_)],
        16: [(0, A_), (2, D_)]}


@dataclass(frozen=True)
class Head:
    measure: int
    index: int               # 1-based note position inside the measure
    q: Fr                    # written onset in quarters from the start of the theme
    dur: Fr
    midi: int
    tie_start: bool
    tie_stop: bool


def read_musicxml(path):
    root = ET.parse(path).getroot()
    part = root.find("part")
    divisions = None
    heads, q = [], Fr(0)
    repeats = []
    for m in part.findall("measure"):
        num = int(m.get("number"))
        idx = 0
        for el in m:
            if el.tag == "attributes":
                d = el.find("divisions")
                if d is not None:
                    divisions = int(d.text)
            elif el.tag == "barline":
                r = el.find("repeat")
                if r is not None:
                    repeats.append((num, r.get("direction")))
            elif el.tag in ("backup", "forward"):
                raise ValueError("measure %d: %s not handled" % (num, el.tag))
            elif el.tag == "note":
                if el.find("chord") is not None or el.find("grace") is not None:
                    raise ValueError("measure %d: chords and grace notes not handled" % num)
                dur = Fr(int(el.find("duration").text), divisions)
                idx += 1
                if el.find("rest") is None:
                    p = el.find("pitch")
                    midi = 12 * (int(p.find("octave").text) + 1) + STEP[p.find("step").text] + int(p.findtext("alter", "0"))
                    ties = {t.get("type") for t in el.findall("tie")}
                    heads.append(Head(num, idx, q, dur, midi, "start" in ties, "stop" in ties))
                q += dur
    return heads, q, repeats


def merge_ties(heads):
    """Merge a tied chain into one note whose duration is the sum. A tie-stop whose start is not in `heads` stays a plain note. Returns [(Head, src)] with the merged head and a source string."""
    out, open_ = [], {}
    for h in sorted(heads, key=lambda x: x.q):
        src = "m%d.%d" % (h.measure, h.index)
        if h.tie_stop and h.midi in open_:
            i = open_.pop(h.midi)
            first, s = out[i]
            merged = Head(first.measure, first.index, first.q, first.dur + h.dur, first.midi, h.tie_start, False)
            out[i] = (merged, s + "+" + src)
            if h.tie_start:
                open_[h.midi] = i
            continue
        out.append((h, src))
        if h.tie_start:
            open_[h.midi] = len(out) - 1
    return out


def tempo_entries(qpm0, bars_before_coda, coda_bars):
    q_rit = Fr(bars_before_coda * BAR_Q)
    n = coda_bars * BAR_Q
    e = [(Fr(0), qpm0)]
    for i in range(n):
        e.append((q_rit + i, max(1, round(qpm0 / (1 + (RIT_RATIO - 1) * i / (n - 1))))))
    return e


def build(xml_path, qpm=QPM0):
    heads, theme_q, repeats = read_musicxml(xml_path)
    if repeats != [(9, "forward"), (16, "backward")] or theme_q != 64:
        raise ValueError("unexpected theme shape: %s, %s quarters" % (repeats, theme_q))
    bars_before_coda = sum(p[2] for p in PLAN[:-1])
    tm = TempoMap(tempo_entries(qpm, bars_before_coda, PLAN[-1][2]))
    form, notes, harmony = [], [], []
    start = Fr(0)
    bar_no = 1
    for sid, label, nbars, ranges, octave, vel in PLAN:
        q0, q1 = start, start + nbars * BAR_Q
        form.append({"id": sid, "rep": 1, "bars": [bar_no, bar_no + nbars - 1], "q0": frac(q0), "q1": frac(q1), "t0": rnd(tm.seconds(q0)), "t1": rnd(tm.seconds(q1)), "label": label})
        pos, cnt = q0, 0
        for a, b in ranges:
            inside = [h for h in heads if a <= h.q < b]
            for h, src in merge_ties(inside):
                q = pos + (h.q - a)
                bar, beat = metric(q, 0, BAR_Q)
                cnt += 1
                n = {"id": "%s.%s1.%s.%s.%04d" % (PIECE, sid, INST, VOICE, cnt), "inst": INST, "voice": VOICE, "layer": "composer", "pitch": h.midi, "vel": vel,
                     "t": rnd(tm.seconds(q)), "dur": rnd(tm.seconds(q + h.dur) - tm.seconds(q)), "bar": bar, "beat": rnd(beat), "section": sid, "rep": 1, "src": src,
                     "q": frac(q), "ql": frac(h.dur), "kbar": h.measure}
                if octave:
                    n["oct"] = octave
                if "+" in src:
                    n["tied"] = src.count("+") + 1
                notes.append(n)
            pos += b - a
        assert pos == q1 or sid in ("Intro", "Coda"), (sid, pos, q1)       # statements are filled by the melody; the intro and the coda are not
        # harmony: the Intro is a D pedal; a statement follows HARM bar by bar over its source bars; the coda quotes the last phrase, then closes V - I
        starts = []
        if sid == "Intro":
            starts = [(q0, D_)]
        else:
            pos2 = q0
            for a, b in ranges:
                for br in range(int(a // BAR_Q) + 1, int(b // BAR_Q) + 1):
                    starts += [(pos2 + (br - 1) * BAR_Q - a + off, ch) for off, ch in HARM[br]]
                pos2 += b - a
            if sid == "Coda":
                starts += [(q0 + 16, A_), (q0 + 24, D_)]
        merged = []
        for i, (a, ch) in enumerate(starts):
            b = starts[i + 1][0] if i + 1 < len(starts) else q1
            if merged and merged[-1][2] == ch:
                merged[-1] = (merged[-1][0], b, ch)
            else:
                merged.append((a, b, ch))
        for a, b, (root, qual) in merged:
            harmony.append({"t": rnd(tm.seconds(a)), "dur": rnd(tm.seconds(b) - tm.seconds(a)), "q": frac(a), "ql": frac(b - a), "key": KEY, "roman": H.roman(root, qual, root, KEY),
                            "root": root, "qual": qual, "pcs": H.pcs_of(root, qual), "bass": root, "tension": round(H.tension(root, qual, KEY), 3), "section": sid, "rep": 1})
        start = q1
        bar_no += nbars
    total_q = start
    card = {
        "schema": SCHEMA, "piece": PIECE, "title": "Ode to Joy (theme of the finale of Symphony No. 9), arranged in six sections",
        "licence": "MIT for the encoding and the arrangement plan; the melody is public domain",
        "source": {"kind": "musicxml", "path": "sources/ode-theme.musicxml", "sha256": sha256_file(xml_path), "edition": "hand-encoded from the public-domain tradition",
                   "encoding": "Loomsong", "licence": "MIT (encoding); melody public domain"},
        "meter": "4/4",
        "perform": {"qpm": qpm, "ritardando": "from bar %d the tempo falls by whole qpm each quarter to 1/%d of the start by the last quarter" % (RIT_FROM_BAR, RIT_RATIO),
                    "vel": {p[0]: p[5] for p in PLAN if p[5]}, "oct": "octaves between the written pitch and where the arrangement sounds the melody; the Score witness checks the written pitch",
                    "bar": "bars count from 1 at the first intro bar; there is no upbeat", "kbar": "the bar of the 16-bar theme the note comes from (1 to 16)",
                    "tied": "number of written heads merged into the note", "harmony": "authored: D and A with G for colour; see score/ode.py HARM"},
        "tempo_map": [{"q": frac(q), "bar": int(q // BAR_Q) + 1, "beat": rnd(q % BAR_Q + 1), "qpm": int(b)} for q, b in tm.e],
        "key_map": [{"t": 0.0, "q": "0", "key": KEY, "section": "Intro", "rep": 1}],
        "form": form, "instruments": [{"id": INST, "layer": "composer", "stem": "stems/mel.wav"}],
        "notes": notes, "harmony": harmony,
        "checks": {"composer_note_heads": len(heads), "theme_notes_after_ties": len(merge_ties(heads)), "bars_performed": sum(p[2] for p in PLAN), "passes": len(PLAN),
                   "quarters_performed": frac(total_q), "seconds": rnd(tm.seconds(total_q)), "performed_notes": len(notes), "grace_notes": 0,
                   "midi_range": [min(h.midi for h in heads), max(h.midi for h in heads)]},
    }
    return card


if __name__ == "__main__":
    c = build(sys.argv[1])
    print(c["checks"])
    print(len(c["notes"]), "notes", len(c["harmony"]), "harmony segments", len(c["tempo_map"]), "tempo entries")
