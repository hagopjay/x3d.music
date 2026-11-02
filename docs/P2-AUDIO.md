# P2: the two masters

Beethoven's *Ode to Joy* and Mozart's *Rondo alla Turca*, each rendered in code from its score card to a pop-master standard, then judged by two witnesses. The signal path and the reasons for every level are in `MIX.md`; this page says what was built, what was measured, what went wrong on the way and what is still unknown.

Grades: **C** a command or test showed it, **L** reasoned or read, **S** not checked.

## What exists

| Piece | File | Length | Voices |
|---|---|---|---|
| *Rondo alla Turca* | `build/audio/turca/turca.master.wav` (48 kHz, 24-bit stereo) | 3:38.9 (the score is 3:32.9; 6 s of ring-out) | 13: a sampled grand piano plays every written note; bass, kick, snare, clap, hat, tom, davul, cymbal, triangle, jingle, pad and brass are synthesised |
| *Ode to Joy* | `build/audio/ode/ode.master.wav` | 3:35.9 (the score is 3:26.9; 9 s of ring-out after the ritardando) | 16, all synthesised: bass, strings, electric piano, lead, brass, choir, pad, kick, snare, clap, rim, hat, tom, cymbal, timpani, clatter. The card has 17 lines: the tune is one of them (`mel`) and the routing table hands it to the others section by section |

Not committed: the audio is rebuilt from the cards (`MIX.md`, "Rebuild and re-check"). Stems for each piece are about 1 GB and stay out of the shared project folder.

Both files are AI-made: nothing is a recording of a performance of either piece. The grand piano is a sampled instrument (single recorded notes), every other voice is synthesis. Each file's metadata says so and credits the piano.

## What was measured (all C, on the finished masters)

| Measure | Turca | Ode | Tool |
|---|---|---|---|
| Integrated loudness | −14.00 LUFS | −14.00 LUFS | pyloudnorm 0.2.0 and ffmpeg 6.1.1 ebur128 agree (aim −14 plus or minus 1) |
| True peak | −1.50 dBTP (ffmpeg −1.3) | −1.50 dBTP (ffmpeg −1.3) | own 4x oversampling, ffmpeg; limit −1.0 |
| Loudness range | 5.9 LU | 7.5 LU | ffmpeg, EBU R128; wanted 4 to 12 |
| Stereo correlation | 0.544; 0.6% of blocks below zero | 0.688; 0.6% | 400 ms blocks |
| Clipping, NaN, DC | none; worst DC 0.00006 | none; worst DC 0.00007 | every stem and the master |
| Onsets against the card | piano 1,245: median 2.5 ms, 95th 7.9 ms; kick 175 and snare 193: median 1.0, 95th 1.2 | kick 249 and snare 169: median 1.0 ms, 95th 1.2 ms | `witnesses/ear.py` (limits: median 5 ms, 95th 15 ms, at least 20 isolated onsets) |
| Master is the sum of its stems | correlation 0.916, lag 0.00 ms | 0.912, 0.00 ms | aligned to 0.2 ms |
| Sub band under the bass band | 11.3 dB | 12.7 dB | Welch spectrum; limit 6 dB |
| Ends in a ring-out | last 100 ms at −114.6 dBFS | −113.5 dBFS | limit −50 |
| Notes rendered | 6,555 (2,810 written, 3,745 band) | 3,101 (327 written, 2,774 band) | the cards |
| Witnesses | Score 26 of 26, Ear 10 of 10 | Score 25 of 25, Ear 10 of 10 | `witnesses/score_check.py`, `witnesses/ear.py` |
| Reproducible | three fresh renders, same sha256 | three fresh renders, same sha256 | on one machine class (`receipts/p2-audio.json`) |

The piano's median of 2.5 ms is inside the limit and is not a timing fault in the mix: the sampler starts each note where the recording first passes minus 50 dB under its own peak (C: `audio/test_audio.py`, synthetic recordings), and the Faust voices start on the exact sample of their written time. What the Ear witness reads is the strongest rise of the high-frequency spectrum near the written time, and it has an offset of its own: a synthetic click at an exact sample reads 1.0 ms early with the drum window and 10.0 ms early with the piano window (C, measured; D-017). The drums' 1.0 ms is therefore the detector, not the drums. How the piano's 2.5 ms splits between the detector on a slower hammer attack and the sampler's start threshold is not separated (L). The witness is trusted for shifts: a sound moved by 20 ms reads 20 ms later (C, `witnesses/test_ear.py`, `Detector`).

## How the work was checked

- **Two loudness tools.** The mix aims with pyloudnorm; the Ear witness reads with pyloudnorm and ffmpeg and fails if they differ by more than 0.3 LU. On the masters they read minus 14.00 and minus 14.0.
- **Ear witness, 20 checks (10 a piece).** `witnesses/test_ear.py` (24 tests) runs it on a 30 s synthetic piece mixed under the same limiter, then on damaged copies: too quiet, too loud, clipped (master and stem), a DC offset, one channel inverted, onsets shifted or a snare missing or one percent of tempo drift, a master 10 ms late against its stems, a master that is not these stems, the wrong sample rate, a stem of another length, flat loudness, sub rumble, a cut ending, a NaN in a stem. Each must turn red the check that owns it. Four more tests hold the onset detector itself.
- **Score witness, 51 checks (26 and 25).** The arrangement layers are held to the composer's notes: every arrangement note names its rule and carries no kern bar (S11); none is played by a composer instrument (S12); every instrument has a declared stem (S13); times follow the tempo map within 0.6 microseconds and nothing starts before the piece or rings past it (S14); pitch and velocity are legal (S15); the Ode's routing gives every section a route to declared instruments (S16); the Ode's counter-line stands a third, fifth or sixth above the tune (S17). `witnesses/test_score_check.py` has 37 tests: the real cards pass, and each damaged copy turns red the check that owns it.
- **Audio unit tests, 43.** `audio/test_audio.py`: the meters, the ducking and gate curves, the rides, the limiter (ceiling, latency, untouched quiet passages, its envelope against the definition), the sampler's rules on synthetic recordings (key choice, layer blend, pitch direction, roll, staccato, slurs), the routing, every Faust voice, every chain's delay.
- **Breaking the code on purpose.** `audio/mutants.py` changes one expression at a time in a scratch copy and runs the test class that should notice: limiter ceiling 3 dB too high, limiter looking only backwards, ducking doubled, ride sign flipped, velocity blend swapped, nearest key made farthest, pitch shifted the wrong way, arpeggio roll 20 ms instead of 18, routing dropping the octave, a Faust note 1 ms late, a 10 ms delay in a chain. C: 11 of 11 turn a test red on an assertion (about 25 s). An error instead of a failed assertion is reported as BROKEN, not as caught; two of the first run's eleven were exactly that (a syntax error and a missing import) and were rewritten.
- **Receipts.** `receipts/p1-scores.json` (rebuilt cards give the same bytes) and `receipts/p2-audio.json` (inputs and master hashes).

## What went wrong, and what fixed it

Only the problems whose evidence is still in the repository are listed with numbers.

| Problem | How it showed | Fix |
|---|---|---|
| pedalboard's limiter was not transparent | a 0.5 impulse came out at 1.0 (probe, `MIX.md`) | our own look-ahead true-peak limiter (`mix.limit`, `MIX.md`; D-015) |
| ffmpeg read minus 1.0 dBTP when our meter read minus 1.2 | Ear E3 on the limit | the ceiling is minus 1.5, where ffmpeg reads minus 1.3 (D-015) |
| The first full masters had a loudness range under the floor of 4 LU | Ear E4 red | fader rides along each piece's loudness arc (`rides_db` in each `report.json`: between minus 2.7 and plus 2.3 dB) |
| A DC offset in the bass stem, over the limit of 0.001 | Ear E5 red | a 24 Hz high-pass at the end of the bass chains (`audio/recipes.py`); worst DC is now 0.00006 and 0.00007 |
| One long onset window read sharp hits 10 ms early | a synthetic click at an exact sample read 10.0 ms early with the piano's 1,024-sample window and 1.0 ms with a 128-sample one | class-specific windows (D-017) |
| A true-peak unit test read plus 0.37 dBTP on a plain tone | ringing of the oversampling filter at an abrupt start and stop | the test tone gets 4,800-sample Hann ramps |
| Two of the first eleven mutants counted as caught without testing anything | a syntax error and a missing import fail any test | rewritten so that each turns an assertion red (`audio/mutants.py` now tells CAUGHT from BROKEN) |

Speed: the stems render in a process pool (`audio/mix.py`) and each instrument's stem is cached by what it depends on (`audio/render.py`), so retuning one voice renders one voice and a change of recipe renders nothing.

An automated listener (a multimodal model given the audio) was run on early mixes. It is advisory and not evidence for anything here: it heard a piano in an early Ode mix, and the Ode has none. No number in this report depends on it.

## Not known yet (S)

- **How it sounds.** No human has listened. Every level was set by metrics. The questions for a listener: do the Turca's drums feel like a record or like a machine; do the 189 grace notes (a 32nd before the beat) read as ornaments or slips; is the velocity map (p 50, f 96, sfp 114 then p; the Ode's per-section 62, 72, 86, 100, 96) right; is the Ode's tune audible as a melody in the bass register of its first section.
- **Other browsers.** The page plays the AAC `.mp4`; its decoding is C in Chrome 153 (P0) and S in Safari and Firefox. The listening page's host self-test measures what the real viewer does.
- **Other machines.** Bit-identical audio is C on one machine and S on others (`MIX.md`); CI uses thresholds.

## Decisions

D-013 to D-018 in `DECISIONS.md`.
