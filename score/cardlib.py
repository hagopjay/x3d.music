#!/usr/bin/env python3
"""Shared pieces of the score cards (schema loomsong.score/1): exact fractions, the tempo map, bar and beat, velocity from dynamics, and a deterministic writer. Stdlib only.

Everything musical is kept as an exact Fraction of a quarter note; seconds are derived from the tempo map and rounded to a microsecond only when written out.
"""
import hashlib, json, math
from fractions import Fraction as Fr

GRACE_Q = Fr(1, 8)           # a grace note is performed as a 32nd, immediately before the beat of the note it decorates
VEL = {"pp": 36, "p": 50, "mp": 62, "mf": 76, "f": 96, "ff": 114}
SF_VEL = 114                 # the accented chord of an sfp
SCHEMA = "loomsong.score/1"


def frac(x):
    x = Fr(x)
    return str(x.numerator) if x.denominator == 1 else "%d/%d" % (x.numerator, x.denominator)


def unfrac(s):
    return Fr(s)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class TempoMap:
    """Piecewise-constant tempo: entries [(q, qpm)] sorted by q, the first at q = 0. seconds() is exact (Fractions) until the final rounding."""

    def __init__(self, entries):
        self.e = [(Fr(q), Fr(b)) for q, b in entries]
        assert self.e and self.e[0][0] == 0 and all(self.e[i][0] < self.e[i + 1][0] for i in range(len(self.e) - 1))
        self.cum = [Fr(0)]
        for i in range(len(self.e) - 1):
            q0, b0 = self.e[i]
            self.cum.append(self.cum[-1] + (self.e[i + 1][0] - q0) * 60 / b0)

    def _i(self, q):
        i = 0
        while i + 1 < len(self.e) and self.e[i + 1][0] <= q:
            i += 1
        return i

    def seconds(self, q):
        q = Fr(q)
        i = self._i(q)
        return self.cum[i] + (q - self.e[i][0]) * 60 / self.e[i][1]

    def spq(self, q):
        """Seconds per quarter note at q."""
        return 60 / self.e[self._i(Fr(q))][1]

    def quarters(self, t):
        t = Fr(t)
        i = len(self.cum) - 1
        while i > 0 and self.cum[i] > t:
            i -= 1
        return self.e[i][0] + (t - self.cum[i]) * self.e[i][1] / 60


def metric(q, pickup, beats):
    """(bar, beat) for an absolute position q in quarters in a piece with `beats` quarters to the bar. beat is 1-based and fractional (1 = the downbeat).
    With an upbeat (0 < pickup < beats) the upbeat is bar 0, sitting on the last beats of that bar, and the first full bar is 1.
    With no upbeat (pickup = 0) the first bar is bar 1."""
    q = Fr(q)
    if pickup:
        x = q + (beats - pickup)
        return int(x // beats), x % beats + 1
    return int(q // beats) + 1, q % beats + 1


def rnd(x, n=6):
    return round(float(x), n)


def velocity_fn(dyn_events):
    """dyn_events: [(q, token)] in performed order, tokens p, f, sfp, <, ... Returns f(q, grace) -> int velocity.
    p and f set the level from their position on. sfp accents whatever starts exactly there, then the level is p. A '<' ramps linearly to the next marking's target."""
    ev = sorted(dyn_events, key=lambda e: e[0])
    segs = []                                    # (q0, level, ramp_to_level or None, q_end or None, accent_at_q0)
    level = VEL["p"]
    i = 0
    while i < len(ev):
        q, tok = ev[i]
        if tok == "<":
            nxt = next((e for e in ev[i + 1:] if e[1] != "<"), None)
            if nxt is None:
                segs.append((q, level, None, None, False))
            else:
                target = SF_VEL if nxt[1] == "sfp" else VEL[nxt[1]]
                segs.append((q, level, target, nxt[0], False))
        elif tok == "sfp":
            segs.append((q, VEL["p"], None, None, True))
            level = VEL["p"]
        else:
            level = VEL[tok]
            segs.append((q, level, None, None, False))
        i += 1

    def f(q):
        cur = None
        for s in segs:
            if s[0] <= q:
                cur = s
            else:
                break
        if cur is None:
            return VEL["mf"]
        q0, lv, target, qe, accent = cur
        if accent and q == q0:
            return SF_VEL
        if target is not None and qe is not None and q < qe:
            return int(round(lv + (target - lv) * float((Fr(q) - q0) / (qe - q0))))
        return lv

    return f


def dump_card(card, path):
    """Deterministic layout: one top-level key per block, one note per line, so a change shows up as a few lines in a diff."""
    def j(o):
        return json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    out = ["{"]
    keys = list(card.keys())
    for ki, k in enumerate(keys):
        v = card[k]
        comma = "," if ki < len(keys) - 1 else ""
        if isinstance(v, list) and v and isinstance(v[0], dict):
            out.append(' "%s": [' % k)
            out.extend("  %s%s" % (j(x), "," if i < len(v) - 1 else "") for i, x in enumerate(v))
            out.append(" ]%s" % comma)
        else:
            out.append(' "%s": %s%s' % (k, j(v), comma))
    out.append("}")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
