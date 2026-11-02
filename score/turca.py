#!/usr/bin/env python3
"""The Rondo alla Turca score card (composer layer, form map, key map, harmony) from the Humdrum kern file. Stdlib only.

build(kern_path, qpm) -> dict in schema loomsong.score/1. The repeat plan is the file's own (`*>[A,A,B,B,...,I,I1,I,I2,J]`); each pass re-plays the notes of its section with
exact Fraction onsets. Grace notes take no written time; in performance they sit just before the beat of the note they decorate, one 32nd each (cardlib.GRACE_Q).
"""
import os, sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kern as K                                   # noqa: E402
import harmony as H                                # noqa: E402
from cardlib import GRACE_Q, SCHEMA, TempoMap, dump_card, frac, metric, rnd, sha256_file, velocity_fn   # noqa: E402

PIECE = "turca"
INST = "pno"
VOICE_ORDER = {"R": 0, "R2": 1, "L": 2}
MIDI_RANGE = (38, 88)
# Hand-checked key map: for each section label, (quarters from the section start, key). Lower case is minor. See docs/HARMONY.md for what was checked and how.
KEYS = {"A": [(0, "a")], "B": [(0, "C"), (8, "a")], "C": [(0, "A")], "D": [(0, "f#")], "E": [(0, "A"), (16, "f#")], "F": [(0, "A")],
        "G": [(0, "a")], "H": [(0, "C"), (8, "a")], "I": [(0, "A")], "I1": [(0, "A")], "I2": [(0, "A")], "J": [(0, "A")]}
LABELS = {"A": "theme, A minor", "B": "C major answer, then A minor", "C": "Janissary refrain, A major", "D": "F sharp minor episode",
          "E": "running sixteenths, A major then F sharp minor", "F": "Janissary refrain, A major", "G": "theme returns, A minor",
          "H": "C major answer, then A minor", "I": "Janissary refrain, A major", "I1": "first ending", "I2": "second ending, into the coda", "J": "coda, A major"}


def sections(k):
    out = {}
    for i, (lab, ln, t0) in enumerate(k.labels):
        t1 = k.labels[i + 1][2] if i + 1 < len(k.labels) else k.end_t
        out[lab] = (t0, t1, ln, k.labels[i + 1][1] if i + 1 < len(k.labels) else 10 ** 9)
    return out


def performed_bars(k, secs):
    """The performed bar count: every numbered kern barline passed in plan order, each barline counted under the label that precedes it in the file (the file's own convention)."""
    n = {lab: sum(1 for b in k.barlines if b["num"] is not None and s[2] <= b["line"] < s[3]) for lab, s in secs.items()}
    return sum(n[x] for x in k.plan), n


def build(kern_path, qpm=126):
    k = K.parse(kern_path)
    secs = sections(k)
    plan = k.plan
    tm = TempoMap([(0, qpm)])
    # -- passes
    form, rep_count, start = [], {}, Fr(0)
    passes = []
    for x in plan:
        w0, w1, _, _ = secs[x]
        rep_count[x] = rep_count.get(x, 0) + 1
        q0, q1 = start, start + (w1 - w0)
        full = [h.kbar for h in k.heads if w0 <= h.t < w1]
        bars = sorted({b for b in full})
        first_full = [b for b in bars if b >= 1]
        passes.append({"id": x, "rep": rep_count[x], "w0": w0, "w1": w1, "q0": q0, "q1": q1})
        form.append({"id": x, "rep": rep_count[x], "bars": [first_full[0], first_full[-1]] if first_full else [], "q0": frac(q0), "q1": frac(q1),
                     "wq0": frac(w0), "t0": rnd(tm.seconds(q0)), "t1": rnd(tm.seconds(q1)), "label": LABELS[x]})
        start = q1
    total_q = start
    # -- dynamics in performed order
    dyn_perf = []
    for p in passes:
        for t, _, tok in k.dyn:
            if p["w0"] <= t < p["w1"]:
                dyn_perf.append((p["q0"] + (t - p["w0"]), tok))
    vel = velocity_fn(dyn_perf)
    # -- notes
    raw = []
    for pi, p in enumerate(passes):
        for h in k.heads:
            if p["w0"] <= h.t < p["w1"]:
                raw.append((pi, p, h, p["q0"] + (h.t - p["w0"])))
    raw.sort(key=lambda r: (r[3], 0 if r[2].grace else 1, VOICE_ORDER[r[2].voice], r[2].line, r[2].col, r[2].sub, r[0]))
    counters, notes = {}, []
    # grace groups: consecutive graces of one voice at one onset in one pass
    gsize = {}
    for pi, p, h, q in raw:
        if h.grace:
            gsize[(pi, h.voice, q)] = gsize.get((pi, h.voice, q), 0) + 1
    gseen = {}
    for pi, p, h, q in raw:
        sec = p["id"] + str(p["rep"])
        cnt = counters.get((sec, h.voice), 0) + 1
        counters[(sec, h.voice)] = cnt
        if h.grace:
            m = gsize[(pi, h.voice, q)]
            i = gseen.get((pi, h.voice, q), 0)
            gseen[(pi, h.voice, q)] = i + 1
            g = GRACE_Q * tm.spq(q)
            t = tm.seconds(q) - (m - i) * g
            dur = g
            ql = Fr(0)
        else:
            t = tm.seconds(q)
            dur = tm.seconds(q + h.dur) - t
            ql = h.dur
        bar, beat = metric(q, 1, 2)
        n = {"id": "%s.%s.%s.%s.%04d" % (PIECE, sec, INST, h.voice, cnt), "inst": INST, "voice": h.voice, "layer": "composer", "pitch": h.midi,
             "vel": vel(q) if not h.grace else max(30, vel(q) - 14), "t": rnd(t), "dur": rnd(dur), "bar": bar, "beat": rnd(beat), "section": p["id"], "rep": p["rep"],
             "src": h.src, "q": frac(q), "ql": frac(ql), "kbar": h.kbar}
        if h.grace:
            n["g"] = 1
        art = ("s" if h.stac else "") + ("a" if h.arp else "") + ("t" if h.trill else "")
        if art:
            n["art"] = art
        if h.slur:
            n["sl"] = h.slur
        notes.append(n)
    # -- harmony per section (written once), mapped onto every pass
    sec_harm = {}
    for lab, (w0, w1, _, _) in secs.items():
        spans = [(h.t, h.t + h.dur, h.midi, h.voice == "L") for h in k.heads if not h.grace and h.t + h.dur > w0 and h.t < w1]
        segs, prev = [], None
        kmap = KEYS[lab]
        for j, (rel, key) in enumerate(kmap):
            a = w0 + rel
            b = w0 + kmap[j + 1][0] if j + 1 < len(kmap) else w1
            out = H.label_section(spans, a, b, key, prev=prev)
            segs += [(s, e, r, ql_, bs, key) for s, e, r, ql_, bs in out]
            if out:
                prev = out[-1][2:]
        sec_harm[lab] = segs
    harmony, key_map = [], []
    for p in passes:
        for s, e, r, qual, bs, key in sec_harm[p["id"]]:
            q0 = p["q0"] + (s - p["w0"])
            q1 = p["q0"] + (e - p["w0"])
            harmony.append({"t": rnd(tm.seconds(q0)), "dur": rnd(tm.seconds(q1) - tm.seconds(q0)), "q": frac(q0), "ql": frac(q1 - q0), "key": key,
                            "roman": H.roman(r, qual, bs, key), "root": r, "qual": qual, "pcs": H.pcs_of(r, qual), "bass": bs,
                            "tension": round(H.tension(r, qual, key), 3), "section": p["id"], "rep": p["rep"]})
            if not key_map or key_map[-1]["key"] != key:
                key_map.append({"t": rnd(tm.seconds(q0)), "q": frac(q0), "key": key, "section": p["id"], "rep": p["rep"]})
    bars_perf, per_sec = performed_bars(k, secs)
    card = {
        "schema": SCHEMA, "piece": PIECE, "title": "Rondo alla Turca (Piano Sonata No. 11 in A major, K. 331, third movement)",
        "licence": "CC BY-NC-SA 4.0: adapted from the encoding credited in NOTICE.md, so share-alike applies to this file",
        "source": {"kind": "kern", "path": "sources/sonata11-3.krn", "sha256": sha256_file(kern_path), "commit": "0f1f49d", "edition": "Alte Mozart-Ausgabe 1878",
                   "encoding": "Craig Stuart Sapp", "licence": "CC BY-NC-SA 4.0", "metronome_in_file": k.meta.get("mm")},
        "meter": k.meta.get("meter", "2/4"),
        "perform": {"qpm": qpm, "grace": "each grace note is a 32nd (1/8 quarter) placed just before the beat of the note it decorates",
                    "vel": "p 50, f 96, sfp 114 then p, '<' ramps to the next marking; grace notes 14 below the note they decorate",
                    "bar": "bar 0 is the upbeat (beat 2 of a 2/4 bar); bar and beat follow the performed quarter position q, so a repeat sign closes bar 8 with the next pass's upbeat",
                    "kbar": "the measure number printed in the kern file; an upbeat carries the number of the bar it completes",
                    "art": "s staccato, a arpeggiated chord, t trill", "sl": "s slur starts, e slur ends"},
        "tempo_map": [{"q": "0", "bar": 0, "beat": 2, "qpm": qpm}],
        "key_map": key_map, "form": form,
        "instruments": [{"id": INST, "layer": "composer", "stem": "stems/pno.wav"}],
        "notes": notes, "harmony": harmony,
        "checks": {"composer_note_heads": len(k.heads), "bars_performed": bars_perf, "passes": len(passes), "quarters_performed": frac(total_q),
                   "seconds": rnd(tm.seconds(total_q)), "performed_notes": len(notes), "grace_notes": sum(h.grace for h in k.heads),
                   "midi_range": [min(h.midi for h in k.heads), max(h.midi for h in k.heads)], "barlines_by_label": per_sec},
    }
    return card


if __name__ == "__main__":
    c = build(sys.argv[1])
    print({k_: v for k_, v in c["checks"].items()})
    print(len(c["notes"]), "notes", len(c["harmony"]), "harmony segments", len(c["key_map"]), "key changes")
