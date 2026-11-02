#!/usr/bin/env python3
"""Build the score cards and the first feature tracks from the notated sources. Stdlib only; deterministic (a rebuild gives the same bytes).

    python3 -I score/build_score.py            # writes score/turca.score.json, score/ode.score.json, tracks/turca.tracks.json, tracks/ode.tracks.json

Run it from anywhere; paths are taken from the repository root. The Score witness (witnesses/score_check.py) then checks every card against its source with a second, independent parser.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ode, tracks, turca                      # noqa: E402
from cardlib import dump_card                  # noqa: E402

JOBS = (("turca", lambda: turca.build(os.path.join(ROOT, "sources", "sonata11-3.krn"))),
        ("ode", lambda: ode.build(os.path.join(ROOT, "sources", "ode-theme.musicxml"))))


def main():
    for piece, make in JOBS:
        card = make()
        cp = os.path.join(ROOT, "score", piece + ".score.json")
        dump_card(card, cp)
        tp = os.path.join(ROOT, "tracks", piece + ".tracks.json")
        tracks.write(tracks.build(card, cp), tp)
        print("%-6s %5d notes %4d harmony segments %3d form passes %7.2f s  -> %s (%d bytes), %s (%d bytes)" % (
            piece, len(card["notes"]), len(card["harmony"]), len(card["form"]), card["checks"]["seconds"], os.path.relpath(cp, ROOT), os.path.getsize(cp),
            os.path.relpath(tp, ROOT), os.path.getsize(tp)))


if __name__ == "__main__":
    main()
