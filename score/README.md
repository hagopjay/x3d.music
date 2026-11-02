# score/

`build_score.py` turns the sources into the score cards `turca.score.json` and `ode.score.json` (schema `loomsong.score/1`, see `docs/SCORE-SCHEMA.md`) and the first feature tracks in `tracks/`. Standard library only; a rebuild gives the same bytes.

| File | What it does |
|---|---|
| `kern.py` | Humdrum **kern reader for the one file this project uses; strict about anything it does not know |
| `turca.py`, `ode.py` | Build one card each: repeat plan or statement plan, exact fractions, ids, grace and velocity rules, key map, harmony |
| `harmony.py` | Chord labelling, Roman numerals, spiral-array tension |
| `cardlib.py` | Fractions, tempo map, bar and beat, velocity, the card writer |
| `tracks.py` | The 60 Hz feature tracks |
| `test_*.py` | Unit tests |

Composer notes are checked against the source by `witnesses/score_check.py`; the arrangement layer is added in P2 on its own ids.
