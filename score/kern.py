#!/usr/bin/env python3
"""A small Humdrum **kern reader, written for the one file this project uses (sources/sonata11-3.krn) and strict about everything else.

    python3 -I score/kern.py sources/sonata11-3.krn          # prints a summary

Every written note head comes out with an exact Fraction onset and duration in quarter notes (the pickup starts at 0), its pitch, the voice it sits in, and the line, column
and chord position it was read from. Spines may split (`*^`) and merge (`*v`), as the right hand does in a few bars. A token character this reader does not know is an error,
not something to skip: a changed source file stops the build instead of changing a note. Stdlib only.

What is read: durations (with dots), pitches and accidentals, rests (also hidden ones), chords, grace notes (`q`), staccato, arpeggio and trill marks, slurs, barlines and their
numbers, section labels `*>X`, the file's repeat plan, the meter, the metronome mark, key signatures, and the `**dynam` spine. Ties and any other exclusive interpretation raise.
"""
import re, sys
from dataclasses import dataclass
from fractions import Fraction as Fr

ALLOWED = set("0123456789.abcdefgABCDEFG#-nryqLJKk'():t X<>/")   # <, > and / are placement marks (above, below, stem up); L J K k are beams; X is an editorial mark
STEP = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class KernError(Exception):
    pass


@dataclass(frozen=True)
class Head:
    line: int          # 1-based line in the file
    col: int           # 1-based physical column on that line (after any spine split)
    sub: int           # 1-based position inside a chord
    voice: str         # L = left hand, R = right hand, R2 = the second right-hand voice while the spine is split
    t: Fr              # written onset, quarters from the start of the file (the pickup starts at 0)
    dur: Fr            # written duration in quarters (0 for a grace note)
    midi: int
    name: str          # scientific pitch name, e.g. G#5
    grace: bool
    stac: bool
    arp: bool
    trill: bool
    slur: str          # '' | 's' (slur starts) | 'e' (slur ends) | 'se'
    kbar: int          # the file's measure number the head sits in (the pickup before bar 1 is 0; a later pickup keeps the number of the bar it completes)

    @property
    def src(self):
        return "%d:%d.%d" % (self.line, self.col, self.sub) if self.sub > 1 else "%d:%d" % (self.line, self.col)


@dataclass
class Kern:
    heads: list
    dyn: list          # (t, line, token) from the **dynam spine
    barlines: list     # dicts: line, t, num (int or None), tok
    labels: list       # (label, line, t) for each *>X section label, in file order
    plan: list         # the repeat plan the file states (*>[A,A,B,...])
    plan_norep: list
    meta: dict
    end_t: Fr


def _dur(token, where):
    m = re.search(r"(\d+)(\.*)", token)
    if not m:
        raise KernError("%s: no duration in %r" % (where, token))
    n = int(m.group(1))
    d = Fr(4, n) if n else Fr(8)                      # a lone 0 is a breve
    add = d
    for _ in range(len(m.group(2))):
        add /= 2
        d += add
    return d


def _pitch(token, where):
    m = re.search(r"([a-g]+|[A-G]+)(#+|-+|n)?", token)
    if not m:
        raise KernError("%s: no pitch in %r" % (where, token))
    letters, acc = m.group(1), m.group(2) or ""
    if len(set(letters)) != 1:
        raise KernError("%s: mixed pitch letters in %r" % (where, token))
    n = len(letters)
    octave = 3 + n if letters[0].islower() else 4 - n
    shift = acc.count("#") - acc.count("-") if acc != "n" else 0
    midi = 12 * (octave + 1) + STEP[letters[0].lower()] + shift
    return midi, "%s%d" % (NAMES[midi % 12], midi // 12 - 1)


def parse_token(tok, where):
    """One space-separated piece of a kern token (a chord member). Returns dict(rest, dur, midi, name, grace, stac, arp, trill, slur)."""
    bad = sorted(set(tok) - ALLOWED)
    if bad:
        raise KernError("%s: character %r not handled in %r (ties, pauses and other marks are errors here)" % (where, bad[0], tok))
    rest = "r" in tok
    out = {"rest": rest, "grace": "q" in tok, "stac": "'" in tok, "arp": ":" in tok, "trill": "t" in tok,
           "slur": ("s" if "(" in tok else "") + ("e" if ")" in tok else ""), "dur": _dur(tok, where), "midi": None, "name": None}
    if not rest:
        out["midi"], out["name"] = _pitch(tok, where)
    return out


class _Col:
    __slots__ = ("kind", "voice", "t")

    def __init__(self, kind, voice, t):
        self.kind, self.voice, self.t = kind, voice, t


def parse(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    heads, dyn, barlines, labels = [], [], [], []
    plan, plan_norep = [], []
    meta = {"keysigs": [], "keys": [], "reference": {}}
    cols = None
    kbar = 0
    for ln, line in enumerate(lines, 1):
        if not line:
            continue
        if line.startswith("!!"):
            m = re.match(r"!!!([A-Za-z0-9]+):\s*(.*)", line)
            if m:
                meta["reference"][m.group(1)] = m.group(2)
            continue
        toks = line.split("\t")
        if line.startswith("!"):
            continue
        if toks[0].startswith("**"):
            kinds = []
            for t in toks:
                if t not in ("**kern", "**dynam"):
                    raise KernError("line %d: exclusive interpretation %s not handled" % (ln, t))
                kinds.append(t[2:])
            voices = iter(["L", "R"])
            cols = [_Col(k, next(voices) if k == "kern" else "dyn", Fr(0)) for k in kinds]
            continue
        if cols is None:
            raise KernError("line %d: data before the exclusive interpretation" % ln)
        if len(toks) != len(cols):
            raise KernError("line %d: %d tokens for %d spines" % (ln, len(toks), len(cols)))
        if toks[0].startswith("*") or any(t in ("*^", "*v", "*-", "*x", "*+") for t in toks):
            cols = _interpretation(ln, toks, cols, meta, labels, lambda a, b: (plan.extend(a), plan_norep.extend(b)))
            continue
        if toks[0].startswith("="):
            kt = {c.t for c in cols if c.kind == "kern"}
            if len(kt) != 1:
                raise KernError("line %d: the spines are not at the same time at a barline: %s" % (ln, sorted(kt)))
            m = re.match(r"=+(\d+)", toks[0])
            if m:
                kbar = int(m.group(1))
            barlines.append({"line": ln, "t": next(iter(kt)), "num": int(m.group(1)) if m else None, "tok": toks[0]})
            continue
        # a data row
        onsets, pending_dyn = set(), []
        for ci, (col, tok) in enumerate(zip(cols, toks)):
            if tok == ".":
                continue
            where = "line %d col %d" % (ln, ci + 1)
            if col.kind == "dynam":
                pending_dyn.append(tok)
                continue
            parts = [parse_token(s, where) for s in tok.split(" ")]
            dur = {p["dur"] for p in parts}
            if len(dur) != 1:
                raise KernError("%s: chord members with different durations in %r" % (where, tok))
            grace = {p["grace"] for p in parts}
            if len(grace) != 1:
                raise KernError("%s: chord mixing grace and normal notes in %r" % (where, tok))
            grace = grace.pop()
            onsets.add(col.t)
            for si, p in enumerate(parts, 1):
                if p["rest"]:
                    continue
                heads.append(Head(ln, ci + 1, si, col.voice, col.t, Fr(0) if grace else p["dur"], p["midi"], p["name"], grace,
                                  p["stac"], p["arp"], p["trill"], p["slur"], kbar))
            if not grace:
                col.t += dur.pop()
        if len(onsets) > 1:
            raise KernError("line %d: spines disagree about the time of this row: %s" % (ln, sorted(onsets)))
        if pending_dyn:
            if not onsets:
                raise KernError("line %d: a dynamics token on a row where no note starts" % ln)
            for tok in pending_dyn:
                dyn.append((next(iter(onsets)), ln, tok))
    # the final barline (==) sits at the end of the content, which may be a rest
    end_t = max([b["t"] for b in barlines] + [h.t + h.dur for h in heads] + [Fr(0)])
    return Kern(heads, dyn, barlines, labels, plan, plan_norep, meta, end_t)


def _interpretation(ln, toks, cols, meta, labels, set_plan):
    now = {c.t for c in cols if c.kind == "kern"}
    # plain interpretations: record the few that matter
    first = toks[0]
    if not any(t in ("*^", "*v", "*-", "*x", "*+") for t in toks):
        if first.startswith("*>"):
            body = first[2:]
            if body.startswith("norep["):
                set_plan([], body[6:-1].split(","))
            elif body.startswith("["):
                set_plan(body[1:-1].split(","), [])
            else:
                if len(now) != 1:
                    raise KernError("line %d: the spines are not at the same time at the label %s" % (ln, first))
                labels.append((body, ln, next(iter(now))))
        elif first.startswith("*M") and "M" not in first[2:3]:
            meta["meter"] = first[2:]
        elif first.startswith("*MM"):
            meta["mm"] = int(first[3:])
        elif first.startswith("*k["):
            meta["keysigs"].append((ln, first))
        elif re.match(r"\*[a-gA-G][#-]?:$", first):
            meta["keys"].append((ln, first))
        return cols
    # spine operations
    out, i = [], 0
    while i < len(cols):
        t = toks[i]
        if t == "*^":
            out.append(_Col(cols[i].kind, cols[i].voice, cols[i].t))
            out.append(_Col(cols[i].kind, cols[i].voice + "2" if cols[i].kind == "kern" else cols[i].voice, cols[i].t))
        elif t == "*v":
            j = i
            while j < len(cols) and toks[j] == "*v":
                j += 1
            group = cols[i:j]
            if len({c.t for c in group}) != 1:
                raise KernError("line %d: spines merge at different times: %s" % (ln, [str(c.t) for c in group]))
            out.append(_Col(group[0].kind, group[0].voice, group[0].t))
            i = j
            continue
        elif t == "*-":
            pass
        elif t in ("*x", "*+"):
            raise KernError("line %d: spine operation %s not handled" % (ln, t))
        else:
            out.append(cols[i])
        i += 1
    return out


def summary(k):
    kinds = {}
    for h in k.heads:
        kinds[h.voice] = kinds.get(h.voice, 0) + 1
    return {"heads": len(k.heads), "by_voice": kinds, "graces": sum(h.grace for h in k.heads), "labels": [x[0] for x in k.labels],
            "plan": ",".join(k.plan), "barlines": len(k.barlines), "end_q": str(k.end_t), "midi": [min(h.midi for h in k.heads), max(h.midi for h in k.heads)],
            "dynamics": sorted({d[2] for d in k.dyn}), "meter": k.meta.get("meter"), "mm": k.meta.get("mm")}


if __name__ == "__main__":
    import json
    print(json.dumps(summary(parse(sys.argv[1])), indent=1))
