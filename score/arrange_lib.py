#!/usr/bin/env python3
"""Shared pieces of the arrangement layer: notes of our own, with their own ids, around the composer's notes. Stdlib only; deterministic.

An arrangement note is a card note with layer "arrangement". Its `src` names the rule that made it ("arr:kit.march"), it has no `kbar`, and the Score witness never lets it touch a composer note.
The arrangement is written in exact quarters from the card's form map, harmony and composer notes; seconds, bars and beats come from the card's tempo map, as for the composer notes.
"""
import bisect
from fractions import Fraction as Fr

from cardlib import TempoMap, frac, metric, rnd, unfrac

Q = Fr(1, 4)                                                  # a sixteenth, the finest grid the arrangement uses


def fit(pc, lo, hi):
    """The lowest MIDI pitch with pitch class `pc` in [lo, hi] (the highest below lo if none fits)."""
    p = lo + ((pc - lo) % 12)
    return p if p <= hi else p - 12


def nearest(pc, centre):
    """The MIDI pitch with pitch class `pc` closest to `centre` (ties go up)."""
    p = centre + ((pc - centre + 6) % 12) - 6
    return p


class Arr:
    """Collects arrangement notes as (q, ql, instrument, pitch, velocity, rule, voice) and turns them into card notes."""

    def __init__(self, card, pickup, beats):
        self.card, self.pickup, self.beats = card, pickup, beats
        self.tm = TempoMap([(unfrac(e["q"]), e["qpm"]) for e in card["tempo_map"]])
        self.passes = [(unfrac(f["q0"]), unfrac(f["q1"]), f["id"], f["rep"]) for f in card["form"]]
        self.starts = [p[0] for p in self.passes]
        self.harm = [(unfrac(h["q"]), unfrac(h["q"]) + unfrac(h["ql"]), h) for h in card["harmony"]]
        self.harm_starts = [h[0] for h in self.harm]
        self.items = []
        self.order = []                                    # instruments in order of first use, for the card's list

    def pass_at(self, q):
        i = bisect.bisect_right(self.starts, Fr(q)) - 1
        return self.passes[i]

    def chord_at(self, q):
        i = bisect.bisect_right(self.harm_starts, Fr(q)) - 1
        return self.harm[max(i, 0)][2]

    def add(self, q, ql, inst, pitch, vel, rule, voice="A"):
        q, ql = Fr(q), Fr(ql)
        assert ql > 0, (inst, q, ql)
        end = self.passes[-1][1]
        if q >= end:
            return
        ql = min(ql, end - q)                              # nothing rings past the card's end
        if inst not in self.order:
            self.order.append(inst)
        self.items.append((q, ql, inst, int(pitch), max(1, min(127, int(vel))), rule, voice))

    def finish(self, piece):
        """Card notes, sorted by time, instrument and pitch; ids count 1..n inside each (section pass, instrument, voice)."""
        rank = {inst: i for i, inst in enumerate(self.order)}
        merged = {}
        for q, ql, inst, pitch, vel, rule, voice in self.items:             # the same instrument and pitch at the same instant is one note: the louder, the longer
            k = (q, inst, pitch, voice)
            if k in merged:
                q_, ql_, inst_, pitch_, vel_, rule_, voice_ = merged[k]
                merged[k] = (q_, max(ql_, ql), inst_, pitch_, max(vel_, vel), rule_ if vel_ >= vel else rule, voice_)
            else:
                merged[k] = (q, ql, inst, pitch, vel, rule, voice)
        notes, counters = [], {}
        for q, ql, inst, pitch, vel, rule, voice in sorted(merged.values(), key=lambda it: (it[0], rank[it[2]], it[3], it[6])):
            _, _, sec, rep = self.pass_at(q)
            key = (sec, rep, inst, voice)
            counters[key] = counters.get(key, 0) + 1
            t = self.tm.seconds(q)
            bar, beat = metric(q, self.pickup, self.beats)
            notes.append({"id": "%s.%s%d.%s.%s.%04d" % (piece, sec, rep, inst, voice, counters[key]), "inst": inst, "voice": voice, "layer": "arrangement", "pitch": pitch, "vel": vel,
                          "t": rnd(t), "dur": rnd(self.tm.seconds(q + ql) - t), "bar": bar, "beat": rnd(beat), "section": sec, "rep": rep, "src": "arr:" + rule, "q": frac(q), "ql": frac(ql)})
        return notes

    def instruments(self, stems_dir="stems"):
        return [{"id": inst, "layer": "arrangement", "stem": "%s/%s.wav" % (stems_dir, inst)} for inst in self.order]
