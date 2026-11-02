#!/usr/bin/env python3
"""The 1982 band around Mozart's piano in the Rondo alla Turca: drum machine, synth bass, pads, brass and the Janissary percussion, written pass by pass from the card.

Nothing here touches a composer note. The band is built from the card's form map (which pass we are in), its harmony (the chord and its bass) and a few composer onsets (the arpeggiated chords the brass doubles).
The grid: downbeats are the odd quarters of the performed grid; every pass starts either on an upbeat (an even quarter, beat 2 of the bar before) or, for the first ending, the second ending and the coda, on a downbeat.
A pass is walked in bar frames that start on a downbeat; a frame that begins before the pass only contributes its second beat. Stdlib only; no random numbers.
"""
from fractions import Fraction as Fr

from arrange_lib import Arr, fit, nearest
from cardlib import unfrac

H = Fr(1, 2)
S = Fr(1, 4)

# What plays in each pass. kit: hat8off (off-beat eighth hats), hat8, hat16, kick, snare, clap, tom; bass: march | tresillo | walk | octave | None;
# pad 0-2 (how much), brass 0-2 (1 = stabs on the downbeat, 2 = also the arpeggiated chords doubled), jan 0-3 (the Janissary band), fill: a snare and tom run in the last quarter.
PLAN = {
    ("A", 1): dict(kit={"hat8off", "kick"}, bass=None, pad=0, brass=0, jan=0, fill=False),
    ("A", 2): dict(kit={"hat8", "kick", "snare"}, bass="march", pad=0, brass=0, jan=0, fill=False),
    ("B", 1): dict(kit={"hat8", "kick", "snare"}, bass="march", pad=1, brass=0, jan=0, fill=False),
    ("B", 2): dict(kit={"hat8", "kick", "snare", "clap"}, bass="march", pad=1, brass=0, jan=0, fill=True),
    ("C", 1): dict(kit={"hat8off", "kick", "snare"}, bass="tresillo", pad=1, brass=1, jan=1, fill=False),
    ("C", 2): dict(kit={"hat8", "kick", "snare", "clap"}, bass="tresillo", pad=1, brass=1, jan=2, fill=True),
    ("D", 1): dict(kit={"hat8off"}, bass="walk", pad=1, brass=0, jan=0, fill=False),
    ("D", 2): dict(kit={"hat8"}, bass="walk", pad=1, brass=0, jan=0, fill=False),
    ("E", 1): dict(kit={"hat8"}, bass="walk", pad=1, brass=0, jan=0, fill=False),
    ("E", 2): dict(kit={"hat8"}, bass="walk", pad=2, brass=0, jan=0, fill=True),
    ("F", 1): dict(kit={"hat8", "kick", "snare", "clap"}, bass="tresillo", pad=1, brass=1, jan=2, fill=False),
    ("F", 2): dict(kit={"hat8", "kick", "snare", "clap"}, bass="tresillo", pad=1, brass=1, jan=3, fill=True),
    ("G", 1): dict(kit={"hat8", "kick", "snare", "clap"}, bass="march", pad=2, brass=0, jan=0, fill=False),
    ("G", 2): dict(kit={"hat8", "kick", "snare", "clap"}, bass="march", pad=2, brass=0, jan=0, fill=True),
    ("H", 1): dict(kit={"hat8", "kick", "snare", "clap"}, bass="march", pad=2, brass=0, jan=0, fill=False),
    ("H", 2): dict(kit={"hat16", "kick", "snare", "clap"}, bass="march", pad=2, brass=1, jan=0, fill=True),
    ("I", 1): dict(kit={"hat16", "kick", "snare", "clap"}, bass="tresillo", pad=2, brass=1, jan=3, fill=False),
    ("I1", 1): dict(kit={"hat16", "kick", "snare", "clap"}, bass="tresillo", pad=2, brass=1, jan=3, fill=False),
    ("I", 2): dict(kit={"hat16", "kick", "snare", "clap"}, bass="tresillo", pad=2, brass=1, jan=3, fill=False),
    ("I2", 1): dict(kit={"hat16", "kick", "snare", "clap"}, bass="tresillo", pad=2, brass=1, jan=3, fill=False),
    ("J", 1): dict(kit={"hat16", "kick", "snare", "clap", "tom"}, bass="octave", pad=2, brass=2, jan=3, fill=False),
}

KICK, SNARE, CLAP, HAT_C, HAT_O, DAVUL, CYMBAL, TRI, JINGLE = 36, 38, 39, 42, 46, 36, 49, 81, 70
BASS_LO, BASS_HI = 33, 44                      # A1 to G#2: below the left hand's octave, in the range a 1982 synth bass fills a room with


def build(card):
    a = Arr(card, pickup=1, beats=2)
    comp = [n for n in card["notes"] if n["layer"] == "composer"]
    arps = [(unfrac(n["q"]), n["pitch"]) for n in comp if "a" in n.get("art", "")]
    for q0, q1, sec, rep in a.passes:
        p = PLAN[(sec, rep)]
        kit, jan = p["kit"], p["jan"]
        first = q0 if q0 % 2 == 1 else q0 - 1                      # the first frame starts on a downbeat; for an upbeat pass that is the bar before the pass
        shift = 1 if q0 % 2 == 0 else 0                             # ... and the first full bar of such a pass is bar 0

        def put(q, ql, inst, pitch, vel, rule):
            if q0 <= q < q1:
                a.add(q, ql, inst, pitch, vel, rule)

        for idx, d in enumerate(range(int(first), int(q1), 2)):
            d, bar = Fr(d), idx - shift
            if "kick" in kit:
                put(d, S, "kick", KICK, 112, "kit.kick")
            if "snare" in kit:
                put(d + 1, S, "snare", SNARE, 104 if d + 1 > q0 else 92, "kit.snare")
                if "clap" in kit:
                    put(d + 1, S, "clap", CLAP, 88, "kit.clap")
            if "hat8" in kit:
                put(d, S, "hat", HAT_C, 52, "kit.hat8")
                put(d + 1, S, "hat", HAT_C, 52, "kit.hat8")
            if "hat8" in kit or "hat8off" in kit:
                put(d + H, S, "hat", HAT_C, 70, "kit.hat8")
                put(d + 1 + H, S, "hat", HAT_C, 70, "kit.hat8")
            if "hat16" in kit:
                for k in range(8):
                    put(d + k * S, S, "hat", HAT_C, (62, 36, 54, 38)[k % 4], "kit.hat16")
                if bar % 4 == 3:
                    put(d + 1 + H, H, "hat", HAT_O, 66, "kit.hat16")
            if "tom" in kit and bar % 2 == 1:
                put(d + 1 + H, S, "tom", 50, 80, "kit.tom")
                put(d + 1 + H + S, S, "tom", 47, 84, "kit.tom")
            if jan >= 1:                                            # the Janissary band
                put(d, H, "davul", DAVUL, 104, "jan.davul")
                for k in range(4):
                    put(d + k * H, H, "triangle", TRI, 58 if k % 2 else 46, "jan.triangle")
            if jan >= 2:
                put(d + 1 + H, S, "davul", DAVUL, 84, "jan.davul")
                put(d + H, S, "jingle", JINGLE, 56, "jan.jingle")
                put(d + 1 + H, S, "jingle", JINGLE, 56, "jan.jingle")
                if bar % 4 == 0:
                    put(d, 4, "cymbal", CYMBAL, 84 if sec != "J" else 96, "jan.cymbal")
            if jan >= 3:
                put(d + 1, S, "davul", DAVUL, 70, "jan.davul")
                put(d + H, S, "tom", 50, 74, "jan.kettle")
                put(d + 1 + H, S, "tom", 45, 78, "jan.kettle")
                if sec == "J" and bar % 2 == 0 and bar % 4 != 0:
                    put(d, 3, "cymbal", CYMBAL, 90, "jan.cymbal")
            if p["brass"] >= 1 and d >= q0:                         # brass stabs on the downbeat: root, fifth, octave
                h = a.chord_at(d)
                r = fit(h["root"], 57, 68)
                for k, pitch in enumerate((r, r + (6 if h["qual"] in ("o", "o7") else 7), r + 12)):
                    put(d, H, "brass", pitch, 86 - 4 * k, "brass.stab")
            if p["bass"]:
                _bass(a, put, p["bass"], d, q0, bar)
        if p["fill"] and q1 % 2 == 0:                               # a run of snare and toms into the next pass, in the last quarter
            for k, v in enumerate((78, 88, 98, 110)):
                put(q1 - 1 + k * S, S, "snare", SNARE, v, "kit.fill")
            if jan >= 2:
                for k, pitch in enumerate((50, 47, 45, 41)):
                    put(q1 - 1 + k * S, S, "tom", pitch, 84 + 6 * k, "kit.fill")
        if p["brass"] >= 2:                                         # in the coda the brass doubles Mozart's arpeggiated chords
            for q, pitch in arps:
                if q0 <= q < q1:
                    put(q, H, "brass", pitch + (12 if pitch < 60 else 0), 96, "brass.double")
    _pads(a)
    _ending(a, comp)
    return a


def _bass(a, put, kind, d, q0, bar):
    """One bar of synth bass; `d` is the downbeat of the frame, `bar` the bar's number inside the pass (the upbeat frame is -1)."""
    h = a.chord_at(max(d, q0))
    root = fit(h["bass"], BASS_LO, BASS_HI)
    fifth = root + 7 if root + 7 <= BASS_HI + 3 else root - 5
    third = root + (3 if h["qual"] in ("m", "o", "o7") else 4)
    if kind == "march":
        put(d, Fr(3, 4), "bass", root, 100, "bass.march")
        put(d + 1, Fr(3, 4), "bass", fifth if bar % 2 == 0 else root, 94, "bass.march")
    elif kind == "tresillo":
        for k, off in enumerate((Fr(0), Fr(3, 4), Fr(3, 2))):
            put(d + off, S if k < 2 else H, "bass", fifth if (k == 2 and bar % 2 == 1) else root, 106 if k == 0 else 92, "bass.tresillo")
    elif kind == "walk":
        nxt = a.chord_at(d + 2)
        nroot = fit(nxt["bass"], BASS_LO, BASS_HI)
        appr = nroot - 1 if nxt["bass"] != h["bass"] else root + 9
        for k, pitch in enumerate((root, third, fifth, appr)):
            put(d + k * H, Fr(2, 5), "bass", pitch, 88 if k % 2 == 0 else 78, "bass.walk")
    elif kind == "octave":
        for k in range(4):
            put(d + k * H, Fr(2, 5), "bass", root + (12 if k % 2 else 0), 104 if k % 2 == 0 else 92, "bass.octave")


def _pads(a):
    """Sustained chords: one pad voicing for each stretch of the same chord; a chord shorter than two quarters is absorbed by the one before it."""
    chords = []
    for q0, q1, h in a.harm:
        if chords and (q1 - q0 < 2 or (chords[-1][2]["root"], chords[-1][2]["qual"]) == (h["root"], h["qual"])):
            chords[-1] = (chords[-1][0], q1, chords[-1][2])
        else:
            chords.append((q0, q1, h))
    for q0, q1, h in chords:
        _, _, sec, rep = a.pass_at(q0)
        pad = PLAN[(sec, rep)]["pad"]
        if pad:
            for pc in h["pcs"]:
                a.add(q0, q1 - q0, "pad", nearest(pc, 62), 40 + 12 * pad, "pad.chord")


def _ending(a, comp):
    """The final unison hit: every voice lands on the last chord of the piece and rings."""
    last = max(unfrac(n["q"]) for n in comp)
    h = a.chord_at(last)
    ql = a.passes[-1][1] - last
    for inst, pitch, vel in (("kick", KICK, 127), ("snare", SNARE, 120), ("davul", DAVUL, 127)):
        a.add(last, ql, inst, pitch, vel, "end.hit")
    a.add(last, 8, "cymbal", CYMBAL, 127, "end.hit")
    r = fit(h["root"], 57, 68)
    for k, pitch in enumerate((r, r + 7, r + 12, r + 16)):
        a.add(last, ql, "brass", pitch, 110 - 3 * k, "end.hit")
    a.add(last, ql, "bass", fit(h["root"], BASS_LO, BASS_HI), 120, "end.hit")
    for pc in h["pcs"]:
        a.add(last, ql, "pad", nearest(pc, 62), 80, "end.hit")
