#!/usr/bin/env python3
"""Chord labelling by template matching, Roman numerals, and tension on Chew's spiral array. Stdlib only.

label_section() reads the sounding notes of one stretch of score and returns beat-by-beat chord labels merged into segments. It is a labelling of what the score does, made by a
transparent rule (duration-weighted pitch classes against triad and seventh templates, a bonus for the bass note, a bonus for chords that belong to the key, a bonus for staying put);
the key per section is a hand-checked table kept in the piece's builder, and docs/HARMONY.md lists what was checked. Grade L for the labels, C for the arithmetic.

Tension (the spec's "distance of the chord centre from the key centre on the spiral array", Elaine Chew's model): a pitch with index k on the line of fifths sits at
P(k) = (r sin(k pi/2), r cos(k pi/2), k h), r = 1, h = 0.365. A chord's centre is the weighted mean of its pitches; a key's centre the weighted mean of its I, V and IV chord centres.
"""
import math
from fractions import Fraction as Fr

QUAL = {"M": (0, 4, 7), "m": (0, 3, 7), "o": (0, 3, 6), "7": (0, 4, 7, 10), "o7": (0, 3, 6, 9)}
# line-of-fifths offsets from the root, in the order of WEIGHTS
FIFTHS = {"M": (0, 1, 4), "m": (0, 1, -3), "o": (0, -3, -6), "7": (0, 1, 4, -2), "o7": (0, -3, -6, -9)}
WEIGHTS = {"M": (0.516, 0.315, 0.168), "m": (0.516, 0.315, 0.168), "o": (0.45, 0.30, 0.25), "7": (0.45, 0.25, 0.17, 0.13), "o7": (0.35, 0.25, 0.20, 0.20)}
R, H = 1.0, 0.365
KEY_W = (0.536, 0.274, 0.190)                                   # I, V, IV
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
STAY = 0.3                                                        # the bonus, in units of the window's weight, for staying on the chord before (an oom-pah bar must not flicker)
MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11}
MINOR_UNION = {0, 2, 3, 5, 7, 8, 9, 10, 11}                      # natural, harmonic and melodic minor together
DEG_MAJOR = {0: "I", 1: "bII", 2: "II", 3: "bIII", 4: "III", 5: "IV", 6: "#IV", 7: "V", 8: "bVI", 9: "VI", 10: "bVII", 11: "VII"}
DEG_MINOR = {0: "I", 1: "bII", 2: "II", 3: "III", 4: "#III", 5: "IV", 6: "bV", 7: "V", 8: "VI", 9: "#VI", 10: "VII", 11: "#VII"}


def tonic_pc(key):
    """'a' -> 9 (minor), 'A' -> 9 (major), 'f#' -> 6, 'C' -> 0."""
    name = key[0].upper() + key[1:]
    return NAMES.index(name), key[0].islower()


def fifths_index(pc, centre):
    """Index of pitch class pc on the line of fifths, chosen in the window centre-5 .. centre+6 so a key's own spelling (F#, C#, G# in A major) stays contiguous."""
    lo = centre - 5
    return lo + ((7 * pc - lo) % 12)


def tonic_index(pc):
    """The usual index of a tonic on the line of fifths: C = 0, G = 1, ... F# = 6, F = -1, Bb = -2."""
    return ((7 * pc + 5) % 12) - 5


def P(k):
    return (R * math.sin(k * math.pi / 2), R * math.cos(k * math.pi / 2), k * H)


def chord_centre(k_root, qual):
    c = [0.0, 0.0, 0.0]
    for off, w in zip(FIFTHS[qual], WEIGHTS[qual]):
        p = P(k_root + off)
        for i in range(3):
            c[i] += w * p[i]
    return c


def key_centre(tonic, minor):
    kt = tonic_index(tonic)
    chords = [(kt, "m" if minor else "M"), (kt + 1, "M"), (kt - 1, "m" if minor else "M")]
    c = [0.0, 0.0, 0.0]
    for (kr, q), w in zip(chords, KEY_W):
        cc = chord_centre(kr, q)
        for i in range(3):
            c[i] += w * cc[i]
    return c, kt


def tension(root, qual, key):
    """Distance on the spiral array between the chord's centre and the key's centre."""
    tonic, minor = tonic_pc(key)
    kc, kt = key_centre(tonic, minor)
    kr = fifths_index(root, kt)
    cc = chord_centre(kr, qual)
    return math.dist(cc, kc)


def roman(root, qual, bass, key):
    """Roman numeral with inversion figures: V, V7, V65, i, iio, iv6, I64 ..."""
    tonic, minor = tonic_pc(key)
    deg = (DEG_MINOR if minor else DEG_MAJOR)[(root - tonic) % 12]
    lead = deg[:len(deg) - len(deg.lstrip("b#"))]
    base = deg.lstrip("b#")
    if qual in ("m", "o", "o7"):
        base = base.lower()
    iv = QUAL[qual]
    rel = (bass - root) % 12
    if len(iv) == 3:
        return lead + base + ("o" if qual == "o" else "") + {iv[0]: "", iv[1]: "6", iv[2]: "64"}.get(rel, "")
    return lead + base + ("o" if qual == "o7" else "") + {iv[0]: "7", iv[1]: "65", iv[2]: "43", iv[3]: "42"}.get(rel, "7")


def label_section(spans, q0, q1, key, win=Fr(1), prev=None):
    """spans: [(start, end, midi, is_bass)] sounding notes (grace notes excluded). Only a note flagged is_bass (the left hand) can be the bass. A window with no left-hand note keeps the chord
    named just before it in the same stretch (an upbeat or a rest is not a chord change); the first window of a stretch takes the key's tonic triad. Labels each window of `win` quarters
    in [q0, q1) and merges equal neighbours. Returns [(q_start, q_end, root, qual, bass_pc)]."""
    tonic, minor = tonic_pc(key)
    scale = (MINOR_UNION if minor else MAJOR_SCALE)
    scale = {(p + tonic) % 12 for p in scale}
    primary = {(tonic + d) % 12 for d in (0, 5, 7)}
    out = []
    q = Fr(q0)
    last = prev          # the chord before this stretch (it earns the staying bonus, even across a key change)
    held = None          # the last chord named inside this stretch (a left-hand rest keeps this, never a chord of the old key)
    while q < q1:
        w = {}
        low, total = None, 0.0
        for a, b, m, is_bass in spans:
            ov = min(b, q + win) - max(a, q)
            if ov > 0:
                ov = float(ov)
                w[m % 12] = w.get(m % 12, 0.0) + ov
                total += ov
                if is_bass and ov >= 0.25 * float(win) and (low is None or m < low):
                    low = m
        if low is None:
            if held is None:
                held = (tonic, "m" if minor else "M", tonic)
            last = held
            out.append((q, q + win, *held))
            q += win
            continue
        w[low % 12] += 0.5 * float(win)
        total += 0.5 * float(win)
        bass = low % 12
        best, best_s = None, -1e9
        for root in range(12):
            for qual, iv in QUAL.items():
                pcs = {(root + i) % 12 for i in iv}
                s = sum(v for p, v in w.items() if p in pcs) - 0.7 * sum(v for p, v in w.items() if p not in pcs)
                if root == bass:
                    s += 0.3 * total
                if pcs <= scale:
                    s += 0.2 * total
                if qual in ("M", "m") and root in primary:
                    s += 0.1 * total
                if qual == "7" and root == (tonic + 7) % 12:
                    s += 0.1 * total
                if qual == "o7":
                    s -= 0.25 * total
                if last is not None and last[0] == root and last[1] == qual:
                    s += STAY * total
                if s > best_s:
                    best, best_s = (root, qual), s
        last = held = (best[0], best[1], bass)
        out.append((q, q + win, best[0], best[1], bass))
        q += win
    merged = []
    for seg in out:
        if merged and merged[-1][2:4] == seg[2:4]:     # same root and quality: one chord, its figure is the bass where it began
            merged[-1] = (merged[-1][0], seg[1]) + merged[-1][2:]
        else:
            merged.append(seg)
    return merged


def pcs_of(root, qual):
    return sorted((root + i) % 12 for i in QUAL[qual])
