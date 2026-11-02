# Facts the build rests on

Grades: **C** confirmed by a command or file whose source is named; **L** likely (read from a reference, or inferred); **S** suspected (not measured). Re-check a fact only when the work changes it, and change its line when you do.

## The music and its sources

| Fact | Value | Grade, source |
|---|---|---|
| *Rondo alla Turca* score | Humdrum kern of the Alte Mozart-Ausgabe (1878), `craigsapp/mozart-piano-sonatas`, `kern/sonata11-3.krn` at commit `0f1f49d`: two staves, 2/4, `*MM112`, a pickup plus 128 bars, 1,613 written note heads, MIDI range 38 to 88 | C, music21 10.5.2 |
| Its form | Twelve labelled sections A to J with their own repeat plan (21 passes); played with every repeat it runs 224 bars (numbered barlines passed) and **447** quarter notes, not 448: 3:59.5 at q = 112, 3:32.9 at q = 126. The first ending is a half bar, the second a whole bar | C, kern reader and Score witness (P1) |
| Its licence | CC BY-NC-SA 4.0 (attribution, non-commercial, share-alike) for the kern file and everything derived from it; the 1878 edition itself is public domain | C, LICENSE.txt in that repository |
| *Ode to Joy* source | No file fetched: the theme is short and public domain, so it is hand-encoded as MusicXML | L |
| music21's own corpus | Holds neither piece | C |

## The audio stack

| Fact | Value | Grade, source |
|---|---|---|
| Installs on Python 3.13 | music21 10.5.2, pedalboard 0.9.26, pyloudnorm 0.2.0, dawdreamer 0.9.0, soundfile 0.14.0, mido 1.3.3. `tinysoundfont` 0.3.7 does not (it builds `pyaudio`) | C, pip |
| Faust synth speed | DawDreamer renders an analog-style bass voice (three saws into a Moog ladder filter) 378 times faster than real time; parameters are addressed `/dawdreamer/<name>` | C, probe, sandbox CPU |
| Mastering reachable | pedalboard (compressor, reverb, limiter) plus pyloudnorm land on -14.0 LUFS integrated | C, probe |

## The browser side (measured in P0, see PROBES.md)

| Fact | Value | Grade, source |
|---|---|---|
| X_ITE | 16.5.1 is the pin (npm tarball, sha512 in `tools/pins.json`). 16.6.0, 16.6.1 and 16.7.0 exist and are untested here | C, npm registry |
| Measuring browser | Chrome for Testing 153.0.8010.12, headless, driven by Playwright 1.63.0, software GL (ANGLE over SwiftShader), no GPU | C |
| Audio decode | AAC in `.mp4`, Opus in `.ogg`, `.mp3` and `.wav` all decode through `decodeAudioData`, with no onset shift against the wav | C, Chrome 153, ffmpeg 6.1.1 encoders |
| X3D 4.1 splats | `GaussianSplats` needs a file declared 4.1; X_ITE 16.5.1 refuses it in a 4.0 file. It draws only if the page's policy lets WebAssembly compile (its sorter is WebAssembly) | C under a policy copy, S on the real host |
| The real host's policy | Not visible from the build sandbox. The policy copy is written from the published page contract: scripts from the page itself, inline and five named CDNs; fetches only from the page itself; no `unsafe-eval` | L |

## The tools that judge the work

| Tool | Pin | Where |
|---|---|---|
| Validator (XSD, 23 semantic checks, profile check) | `hagopjay/x3d_mcp` commit `327c5c4ee21268fcb5c4526da7c2f39932019e72` | `tools/pins.json` |
| Gate (11 rules) and receipt tool | `hagopjay/x3d.onto` commit `21f5792bcf551137678ccbfaf2fde93ada432615` | `tools/pins.json` |
| Five Loomsong trap rules | this repository, `witnesses/loomsong_rules.py` | until proposed upstream |
| Leak sweep | this repository, `witnesses/leak_sweep.py` | CI, every push |

## Limits of the page host (from the page contract)

A published page is one HTML file plus supporting files; each file at most 16 MB, one publish at most 64 MB, one version at most 256 MB, standard web media types only. Large arrays ship as gzip plus base64 `.txt` parts of at most 9 MB and are decoded in the page. `.x3d` files go out as `application/xml` with the DOCTYPE stripped. (L, contract text; the first stop-and-show page measures what the host really serves.)

## The score cards (P1, see P1-SCORES.md)

| Fact | Value | Grade, source |
|---|---|---|
| Written note heads in the kern file | 1,613 (right hand 790, left hand 776, right hand's second voice 47; 189 grace notes); the project's own reader and music21 10.5.2 agree on every head | C, Score witness S1 |
| Section extents | By content: A 1-8, B 9-24, C 25-32, D 33-40, E 41-56, F 57-64, G 65-72, H 73-88, I 89-95, I1 96, I2 97, J 98-128 (the file puts each `*>` label after the barline it names) | C |
| Dynamics in the file | p, f, sfp and two `<` hairpins, 14 markings in all | C |
| Ties in the kern file | None. Slurs 130, staccato 339, arpeggio marks 24, trills 2 | C |
| The Ode theme | 16 written bars, 63 note heads, 62 notes after the one tie; a statement is 16 bars, or 24 with bars 9 to 16 repeated | C, music21 10.5.2 on the hand-encoded MusicXML |

## The masters (P2, see P2-AUDIO.md and MIX.md)

| Fact | Value | Grade, source |
|---|---|---|
| Piano samples | Salamander Grand Piano V3, Alexander Holm, remapped to SFZ and FLAC by kinwie, CC BY 3.0; 17 keys by 8 velocity layers is 136 files, 212 MB, each with its sha256 in `sources/salamander.manifest.json` | C, the manifest, `tools/fetch_salamander.py` |
| Voices | The Turca has 13 (the sampled piano plus 12 synthesised), the Ode 16 (all synthesised); 19 Faust programs in all, played through DawDreamer 0.9.0 | C, `report.json`, `audio/faust/` |
| Notes rendered | Turca 6,555 (2,810 written, 3,745 arrangement); Ode 3,101 (327 written, 2,774 arrangement) | C, the cards |
| Loudness | Both masters minus 14.00 LUFS by pyloudnorm 0.2.0 and minus 14.0 by ffmpeg 6.1.1 | C, Ear witness E2 |
| True peak | Minus 1.50 dBTP by our 4x oversampling, minus 1.3 by ffmpeg, against a limit of minus 1.0 | C, Ear witness E3 |
| Loudness range, correlation | Turca 5.9 LU and 0.544; Ode 7.5 LU and 0.688 | C, Ear witness E4, E6 |
| Onsets against the card | Drums: median 1.0 ms, 95th percentile 1.2 ms (kick and snare, both pieces). Piano: median 2.5 ms, 95th 7.9 ms, with a detector whose own offset is not zero | C for the numbers, L for the cause, Ear witness E7 |
| Reproducibility | Three fresh renders of each piece gave the same sha256 on one machine (Turca `ca1ba2b5...`, Ode `b4cbd676...`); another CPU may differ in the last bit | C on this machine, S elsewhere, `receipts/p2-audio.json` |
| Tests | 43 audio unit tests, 24 Ear-witness tests, 37 Score-witness tests; 11 of 11 deliberate breakages of the audio code turn a test red | C, `audio/test_audio.py`, `witnesses/test_ear.py`, `witnesses/test_score_check.py`, `audio/mutants.py` |
| Run time | A clean replay of the CI audio job (fresh virtualenv, empty sample cache, 4 cores): pip install 30 s, sample fetch 7 s, unit tests 12 s, mutation check 24 s, both masters 266 s (Ode stems 40.6 s and mix 78.1 s, Turca stems 38.2 s and mix 59.1 s), Ear witness 74 s, its tests 52 s; the masters came out with the receipt's sha256 | C, a log of that replay (not committed) |
| Licences of the audio tools | pedalboard 0.9.26 and DawDreamer 0.9.0 are GPL-3.0 (their package metadata); our code is MIT and does not contain theirs | C, package metadata; what that means for the sound is not settled here (NOTICE.md) |
| How it sounds | Nobody has listened; every level was set by meters | S |
