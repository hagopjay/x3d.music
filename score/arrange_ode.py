#!/usr/bin/env python3
"""The 1982 band around Beethoven's theme in the Ode to Joy: drone and clatter, a bass groove, a counter-line, drum machine, brass, timpani, choir and the one big hit, written section by section from the card.

Nothing here touches a composer note. The melody ("mel") is routed to the instruments of each statement (ROUTING below, stored on the card as `routing`): bass and low strings alone, then cellos and a warm electric
piano, then violins and the lead synth, then everyone. What this module writes is the rest: the intro, the drums, the bass, the counter-line of the second statement, pads and choir, the stabs, the timpani and the
coda's build into its one hit. Positions are exact quarters from the card's form map and harmony (4/4, no upbeat; the card's tempo map, with its coda ritardando, turns them into seconds). Stdlib only; no random numbers.
"""
from fractions import Fraction as Fr

from arrange_lib import Arr, fit, nearest
from cardlib import unfrac

Q, H = Fr(1, 4), Fr(1, 2)
KICK, SNARE, RIM, CLAP, HAT_C, HAT_O, CYMBAL = 36, 38, 37, 39, 42, 46, 49
TOMS = (50, 47, 45, 43)
BASS_LO, BASS_HI = 33, 44                                  # A1 to G#2, as in the Turca
TIMP_LO, TIMP_HI = 36, 47
D_MAJOR = {2, 4, 6, 7, 9, 11, 1}
CONSONANT = {3, 4, 7, 8, 9}                                # semitones (mod 12) the counter-line may stand from the melody note it sounds with: thirds, the fifth, sixths
PHRASE_ENDS = (3, 7, 15, 23)                               # bar index inside a 24-bar statement where the melody lands on a half note (beat 3): Beethoven's phrase ends

# The melody's routing. Each entry: the sounding instrument, `rel` octaves from where the card sounds the melody (its `oct` already moves it per statement), `vel` added to the note's velocity.
ROUTING = {"mel": {
    "S1": [dict(inst="bass", rel=0, vel=6), dict(inst="strings", rel=0, vel=-6)],
    "S2": [dict(inst="strings", rel=0, vel=0), dict(inst="ep", rel=0, vel=6)],
    "S3": [dict(inst="strings", rel=0, vel=-4), dict(inst="lead", rel=0, vel=0)],
    "S4": [dict(inst="strings", rel=0, vel=-2), dict(inst="strings", rel=-1, vel=-8), dict(inst="brass", rel=-1, vel=-10), dict(inst="lead", rel=0, vel=-8)],
    "Coda": [dict(inst="strings", rel=0, vel=-2), dict(inst="strings", rel=-1, vel=-8), dict(inst="brass", rel=-1, vel=-10), dict(inst="lead", rel=0, vel=-8), dict(inst="choir", rel=0, vel=-12)],
}}


def routing(card):
    return ROUTING


def euclid(k, n=16):
    """The k onsets of the Euclidean rhythm over n steps: the loom's clatter thickens one onset at a time."""
    return [i for i in range(n) if (i * k) % n < k]


def build(card):
    a = Arr(card, pickup=0, beats=4)
    for r in ROUTING["mel"].values():                          # the routed instruments are part of the card's instrument list even where no arrangement note names them
        for x in r:
            if x["inst"] not in a.order:
                a.order.append(x["inst"])
    mel = sorted((unfrac(n["q"]), unfrac(n["q"]) + unfrac(n["ql"]), n["pitch"] + 12 * n.get("oct", 0)) for n in card["notes"] if n["layer"] == "composer")
    sec = {f["id"]: (unfrac(f["q0"]), unfrac(f["q1"])) for f in card["form"]}

    def sounding(q0, q1):
        return [p for s, e, p in mel if s < q1 and e > q0]

    def put(q, ql, inst, pitch, vel, rule, voice="A"):
        a.add(q, ql, inst, pitch, vel, rule, voice)

    def root_low(q):
        return fit(a.chord_at(q)["bass"], BASS_LO, BASS_HI)

    def roll(q, n, inst, pitch, v0, v1, rule, step=Q):
        for i in range(n):
            put(q + i * step, step, inst, pitch[i % len(pitch)] if isinstance(pitch, tuple) else pitch, round(v0 + (v1 - v0) * i / max(1, n - 1)), rule)

    def segments(q0, q1, longest=Fr(8)):
        """The card's harmony segments inside [q0, q1), clipped to it, consecutive segments of one chord joined (a pad holds through a repeated chord) up to `longest` quarters."""
        out = []
        for s, e, h in a.harm:
            if s < q1 and e > q0:
                s, e = max(s, q0), min(e, q1)
                if out and out[-1][2]["root"] == h["root"] and out[-1][2]["qual"] == h["qual"] and e - out[-1][0] <= longest:
                    out[-1] = (out[-1][0], e, out[-1][2])
                else:
                    out.append((s, e, h))
        return out

    def voicing(h, q0, q1, centre, with_ninth):
        """The chord's triad around `centre` (nearest octave of each pitch class), plus the ninth when it stands a whole tone or more from every melody note under it."""
        notes = [nearest(pc, centre) for pc in h["pcs"]]
        if with_ninth:
            nine = nearest((h["root"] + 2) % 12, centre + 7)
            if all((nine % 12 - m % 12) % 12 not in (1, 11) for m in sounding(q0, q1)):
                notes.append(nine)
        return sorted(set(notes))

    # --- Intro: the loom wakes. A drone on the tonic, a felt heartbeat on 1 and 3, and the clatter of cards that thickens bar by bar.
    i0, i1 = sec["Intro"]
    for pitch, start, vel in ((38, 0, 54), (45, 0, 46), (50, 8, 44), (57, 16, 40)):
        put(Fr(start), i1 - Fr(start), "pad", pitch, vel, "intro.drone")
    for bar, d in enumerate(range(int(i0), int(i1), 4)):
        for beat in (0, 2):
            put(Fr(d + beat), Q, "kick", KICK, 48 + 4 * bar + (6 if beat == 0 else 0), "intro.heartbeat")
        for j, step in enumerate(euclid((1, 2, 2, 3, 4, 5, 7, 9)[bar])):
            put(Fr(d) + step * Q, Q, "clatter", (67, 72, 76, 79)[j % 4], (84 if step == 0 else 56) + 3 * bar, "intro.clatter")

    # --- Statement 2: the tenor melody, a counter-line a tenth or so above it, kick, rim and eighth hats, the bass groove.
    s0, s1 = sec["S2"]
    prev = 69
    q = s0
    while q < s1:
        for length in (Fr(2), Fr(1)):
            h = a.chord_at(q)
            if q + length > min((e for s, e, hh in a.harm if s <= q < e), default=s1):
                continue                                           # a note does not cross a chord change
            under = sounding(q, q + length)
            cand = [p for p in range(62, 79) if p % 12 in D_MAJOR and all(p > m and (p - m) % 12 in CONSONANT for m in under)]
            chord = [p for p in cand if p % 12 in h["pcs"]]
            cand = chord or cand
            if cand:
                p = min(cand, key=lambda x: (abs(x - prev), x))
                put(q, length, "lead", p, 54, "counter.line")
                prev = p
                q += length
                break
        else:
            q += 1                                                 # nothing is consonant with what the melody does here: the counter-line rests a beat
    for d in range(int(s0), int(s1), 4):
        d = Fr(d)
        put(d, Q, "kick", KICK, 100, "kit.kick")
        put(d + 2, Q, "kick", KICK, 90, "kit.kick")
        put(d + 1, Q, "rim", RIM, 84, "kit.rim")
        put(d + 3, Q, "rim", RIM, 84, "kit.rim")
        for k in range(8):
            put(d + k * H, Q, "hat", HAT_C, 56 if k % 2 == 0 else 72, "kit.hat8")
        for off, shift, ql, vel in ((0, 0, H, 100), (H, 0, H, 80), (Fr(3, 2), 12, H, 84), (2, 0, H, 96), (Fr(5, 2), 0, H, 80), (Fr(7, 2), 7, H, 84)):
            put(d + off, ql, "bass", root_low(d + off) + shift, vel, "bass.groove")

    # --- Statements 3 and 4: the full drum machine, the octave bass, stabs at the phrase ends; the fourth adds timpani, claps, choir and a crash every eight bars.
    for name, loud in (("S3", 0), ("S4", 1)):
        s0, s1 = sec[name]
        for bar, d in enumerate(range(int(s0), int(s1), 4)):
            d = Fr(d)
            for beat, vel in enumerate((112, 98, 104, 98)):
                put(d + beat, Q, "kick", KICK, vel + 4 * loud, "kit.kick")
            for beat in (1, 3):
                put(d + beat, Q, "snare", SNARE, 108 + 6 * loud, "kit.snare")
                if loud:
                    put(d + beat, Q, "clap", CLAP, 98, "kit.clap")
            for k in range(16):
                put(d + k * Q, Q, "hat", HAT_C, (62, 36, 54, 38)[k % 4] + 6 * loud, "kit.hat16")
            if bar % 2 == 1:
                put(d + Fr(7, 2), H, "hat", HAT_O, 70 + 6 * loud, "kit.hat16")
            for k in range(8):                                     # the octave bass: low on the beat, high between
                put(d + k * H, Fr(3, 8), "bass", root_low(d + k * H) + (0 if k % 2 == 0 else 12), (100 if k % 2 == 0 else 84) + 6 * loud, "bass.octaves")
            if bar % 4 == 3:                                       # the fill into the next phrase: a snare run on the last beat, toms under it
                roll(d + 3, 4, "snare", SNARE, 66, 108, "kit.fill")
                roll(d + 3, 4, "tom", TOMS, 74, 100, "kit.fill")
            if bar in PHRASE_ENDS:                                 # the stab on the half note that closes the phrase
                h = a.chord_at(d + 2)
                for p in [nearest(pc, 64) for pc in h["pcs"]] + [nearest(h["root"], 74)]:
                    put(d + 2, Fr(3, 2), "brass", p, 100 + 6 * loud, "brass.stab")
            if loud:
                for beat in (0, 2):
                    put(d + beat, H, "timp", fit(a.chord_at(d + beat)["bass"], TIMP_LO, TIMP_HI), 100 if beat == 0 else 88, "timp.beat")
                if bar % 4 == 3:
                    roll(d + 2, 8, "timp", fit(a.chord_at(d + 2)["bass"], TIMP_LO, TIMP_HI), 60, 112, "timp.roll")
        for seg0, seg1, h in segments(s0, s1):                     # pads (and the choir in the fourth) sustain the harmony, two bars at most
            for p in voicing(h, seg0, seg1, 55, True):
                put(seg0, seg1 - seg0, "pad", p, 54 + 6 * loud, "pad.chord")
                if loud:
                    put(seg0, seg1 - seg0, "choir", p + 12, 60, "choir.chord")
        crashes = [s0] + ([s0 + 32, s0 + 64] if loud else [])
        for c in crashes:
            put(c, Fr(4), "cymbal", CYMBAL, 104 + 8 * loud, "kit.crash")
    # the fill that lets the full kit in, and the one that lets the tutti in: a bar of snare run before each
    for name in ("S3", "S4"):
        roll(sec[name][0] - 2, 8, "snare", SNARE, 56, 112, "kit.build")
        roll(sec[name][0] - 2, 8, "tom", TOMS, 60, 100, "kit.build")

    # --- Coda: the heartbeat comes back while the tempo falls; the dominant builds on timpani and snare; then the one big hit.
    c0, c1 = sec["Coda"]
    hit = c1 - 8                                                   # the tonic bar of the card's authored cadence (V from 368, I from 376)
    for d in range(int(c0), int(hit) - 8, 4):
        d = Fr(d)
        for beat in (0, 2):
            put(d + beat, Q, "kick", KICK, 100, "kit.kick")
            put(d + beat, H, "timp", fit(a.chord_at(d + beat)["bass"], TIMP_LO, TIMP_HI), 96, "timp.beat")
        for beat in (1, 3):
            put(d + beat, Q, "snare", SNARE, 100, "kit.snare")
            put(d + beat, Q, "clap", CLAP, 90, "kit.clap")
        for k in range(8):
            put(d + k * H, Q, "hat", HAT_C, 56 if k % 2 == 0 else 70, "kit.hat8")
    for seg0, seg1, h in segments(c0, hit - 8):
        put(seg0, seg1 - seg0, "bass", root_low(seg0), 104, "bass.root")
        for p in voicing(h, seg0, seg1, 55, True):
            put(seg0, seg1 - seg0, "pad", p, 60, "pad.chord")
            put(seg0, seg1 - seg0, "choir", p + 12, 64, "choir.chord")
    dom = fit(a.chord_at(hit - 8)["bass"], TIMP_LO, TIMP_HI)       # the dominant bars: a roll on the timpani that grows over two bars, a snare run in the second
    roll(hit - 8, 32, "timp", dom, 48, 118, "timp.roll")
    roll(hit - 4, 16, "snare", SNARE, 60, 116, "kit.build")
    roll(hit - 4, 16, "tom", TOMS, 60, 108, "kit.build")
    put(hit - 8, Fr(8), "bass", root_low(hit - 8), 104, "bass.root")
    for p in voicing(a.chord_at(hit - 8), hit - 8, hit, 55, False):
        put(hit - 8, Fr(8), "strings", p, 58, "strings.chord")
        put(hit - 8, Fr(8), "choir", p + 12, 66, "choir.chord")
    # the hit, on the tonic: everything at once, held for the two bars that are left
    h = a.chord_at(hit)
    stack = [fit(h["root"], 38, 49) + k for k in (0, 12, 24)] + [nearest(pc, 62) for pc in h["pcs"] if pc != h["root"]] + [nearest(pc, 74) for pc in h["pcs"] if pc != h["root"]]
    for p in sorted(set(stack)):
        put(hit, Fr(8), "strings", p, 112, "hit.strings")
        put(hit, Fr(8), "choir", p + 12 if p < 70 else p, 100, "hit.choir")
        put(hit, Fr(8), "pad", p, 80, "hit.pad")
    for p in sorted(set(stack))[1:5]:
        put(hit, Fr(4), "brass", p, 118, "hit.brass")
    put(hit, Fr(8), "bass", root_low(hit), 118, "hit.bass")
    put(hit, Fr(8), "timp", fit(h["root"], TIMP_LO, TIMP_HI), 127, "hit.timp")
    put(hit, Fr(4), "kick", KICK, 127, "hit.kick")
    put(hit, Fr(2), "snare", SNARE, 120, "hit.snare")
    put(hit, Fr(2), "clap", CLAP, 112, "hit.clap")
    put(hit, Fr(8), "cymbal", CYMBAL, 127, "hit.crash")
    put(hit, Fr(2), "tom", TOMS[0], 120, "hit.tom")
    return a
