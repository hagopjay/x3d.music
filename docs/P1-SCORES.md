# P1 score cards

Built 2 Nov 2026. Every line carries a grade: **C** confirmed by a command whose output is kept (the Score witness, the unit tests, the receipts), **L** likely (a judgement or a reading), **S** suspected (not measured). Every number names the tool and version behind it.

**Setup (C).** Python 3.13; the builders (`score/*.py`) use the standard library only. music21 10.5.2 is used by the Score witness alone, as the second parser. Sources: `sources/sonata11-3.krn` (sha256 `20986000444bfce9...`, the Humdrum encoding credited in `NOTICE.md`; the commit `0f1f49d` comes from the research fetch that cached it, L) and `sources/ode-theme.musicxml`, hand-encoded from the spec's table (63 note heads). Re-run: `python3 -I score/build_score.py`, then `python3 -I witnesses/score_check.py` (needs `requirements-score.txt`). A rebuild gives the same bytes (`receipts/p1-scores.json`).

## Summary

| # | Question | Answer | Grade | What it changes |
|---|---|---|---|---|
| 1 | Does the kern reader find every written note head, with the right pitch, onset and length? | Yes: 1,613 heads (790 right hand, 776 left, 47 in the right hand's second voice, 189 of them grace notes). music21 10.5.2 finds the same 1,613 with the same onset, pitch, quarter length and grace flag: 0 missing, 0 extra | C | Nothing: the count matches the spec |
| 2 | What does the file's own repeat plan perform? | 21 passes (`A A B B C C D D E E F F G G H H I I1 I I2 J`), **224 bars** by numbered barlines, but **447 quarters**, not 448: the first ending is a half bar that closes into the next pass's upbeat, the second ending a whole bar. 3:32.9 at q = 126, 3:59.5 at q = 112 | C, Score witness S3c, S3d | The spec's "448 quarters, 4:00 and 3:33" is corrected to 447 (4:00 is 239.5 s) |
| 3 | Which bars belong to which section? | By content: A 1-8, B 9-24, C 25-32, D 33-40, E 41-56, F 57-64, G 65-72, H 73-88, I 89-95, I1 96, I2 97, J 98-128. The earlier section script gave each barline to the label above it (I 89-96, I1 97, I2 98, J 99-128); the file puts each label after the barline it names | C, kern reader and the independent left-hand count | The coda starts at kern bar 98, not 99. Every other section is unchanged |
| 4 | Does the form map reproduce the plan, the upbeats and the barlines? | Each pass starts with its own one-quarter upbeat and ends on a half bar (except the second ending), so every pass is an even number of quarters and the bar grid never shifts: the upbeat is bar 0, beat 2; bar 8 is closed by the next pass's upbeat | C, S5 (bar and beat of 2,810 notes) | Bars are counted on the performed grid; the file's own numbers are kept as `kbar` |
| 5 | Ode: does the card follow the spec's table? | Yes: 96 bars (intro 8, statements 16, 16, 24, 24, coda 8), 327 melody notes (62 + 62 + 94 + 94 + 15) from 63 written heads; the tie from bar 12 into bar 13 is one F sharp of two quarters in each full pass (six passes), and the coda's quote of bar 13 starts a fresh attack | C, S1, S2d, S3e | Nothing |
| 6 | Does the witness fail when a card is damaged? | Yes: 19 damaged-card cases go red on the check meant to catch them (pitch, dropped or extra note, moved onset, seconds, grace time, duplicate id, section label, source hash, bar count, a missing pass, a hole in the harmony, an edited tension, tracks that differ from the card, tracks bound to another card, the broken tie, a missing coda note, the wrong form, an edited tempo map); one case that must stay green does (changing velocity, which is performance and not source) | C, `witnesses/test_score_check.py` | Nothing |
| 7 | Do the 60 Hz tracks match the card? | Yes: at 300 random samples plus the first and last, every exact channel equals a brute-force recomputation from the card, in both pieces: 0 differences | C, Score witness T1 | Nothing |
| 8 | Is the harmony right? | It is a labelling, not a proof. Template matching per beat (bass from the left hand only; a beat without a left-hand note keeps the chord before it) plus a hand-checked key table; 195 segments for the Turca, 128 authored for the Ode | L (labels), C (arithmetic: S7) | Look at it in the first lit still; fix the table, not the code |

## What a card holds

`score/<piece>.score.json`, schema `loomsong.score/1` (`docs/SCORE-SCHEMA.md` has every field). The composer layer only: nothing here has been added to what the source says. The arrangement layer joins in P2, on its own ids, and the Score witness keeps checking that the composer notes never change.

| Piece | Notes | Passes | Length | Keys | Harmony |
|---|---|---|---|---|---|
| Turca | 2,810 performed (from 1,613 written heads; 282 graces, 652 staccato, 24 arpeggiated) | 21 | 212.86 s at q = 126 (447 quarters) | a, C, A, f sharp (18 changes) | 195 segments, tension 0.31 to 1.33 |
| Ode | 327 melody notes | 6 | 206.88 s at q = 116 with the coda ritardando (384 quarters) | D | 128 segments (I, V, IV), tension 0.36 to 0.99 |

Tracks (`tracks/<piece>.tracks.json`, 60 Hz): beat phase, bar phase, section, harmony index, tension, density, melody contour, register low and high, notes sounding. All Exact in the spec's sense (computed from the card alone). Loudness and brightness are Texture and come from the rendered audio in P2.

## Turca key map (hand-checked, L)

The table is in `score/turca.py` (`KEYS`); `docs/HARMONY.md` says how it was checked.

| Section | Key | Why |
|---|---|---|
| A, G | a | The theme; both end on the dominant for the repeat (Krumhansl-Schmuckler on the section reads E, the dominant, which is what a half cadence does) |
| B, H | C for 8 quarters, then a | The "C major answer" is the first four bars: C, Em, G, C chords; then A minor with E and G sharp diminished |
| C, F, I, I1, I2, J | A | The refrains and the coda: I, IV, V chords over a tonic-dominant bass |
| D | f sharp | Half cadence on C sharp at the end |
| E | A for 16 quarters, then f sharp | Not a plain "F sharp minor episode": the first two thirds are A major (A, C sharp minor, E7, B minor) before F sharp minor returns |

## Corrections to the spec (all C)

1. 448 quarters is 447. The cause is the second ending (item 2).
2. The coda starts at kern bar 98 by content, not 99 (item 3).
3. Sections D and E are not both "the F sharp minor episode": E spends its first half in A major (key map above).
4. The first ending and the second ending are different lengths (1 quarter and 2), so "I, I1, I, I2" is 15 + 1, then 15 + 2.

## Still S, or left for P2

- **Grace notes.** They take no written time. The cards place them just before the beat of the note they decorate, a 32nd (1/8 quarter, 60 ms at q = 126) each, the usual modern reading for this movement's grace-note turns. How it sounds is S until stop-and-show 1.
- **Velocity.** p 50, f 96, sfp 114 then p, a ramp where the score has `<`: a first guess for the sampler's layers.
- **Harmony of an upbeat.** A beat in which the left hand is silent keeps the chord before it, and a stretch's first beat takes the tonic, so the Turca's opening upbeat (B A G sharp A) is A minor. The first version of the labeller called it G sharp diminished (`docs/HARMONY.md` says what changed and why). Whether a one-beat chord is a real change or a passing one stays a judgement (L).
- **The Ode's colours.** `oct` records the register the arrangement plays the melody in (statement 1 two octaves down, statement 2 one down); the instruments for each statement are chosen in P2 and may split `mel` into several ids then.
- **Arrangement layer, stems, the sampler:** P2.
