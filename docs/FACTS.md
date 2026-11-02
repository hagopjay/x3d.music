# Facts the build rests on

Grades: **C** confirmed by a command or file whose source is named; **L** likely (read from a reference, or inferred); **S** suspected (not measured). Re-check a fact only when the work changes it, and change its line when you do.

## The music and its sources

| Fact | Value | Grade, source |
|---|---|---|
| *Rondo alla Turca* score | Humdrum kern of the Alte Mozart-Ausgabe (1878), `craigsapp/mozart-piano-sonatas`, `kern/sonata11-3.krn` at commit `0f1f49d`: two staves, 2/4, `*MM112`, a pickup plus 128 bars, 1,613 written note heads, MIDI range 38 to 88 | C, music21 10.5.2 |
| Its form | Twelve labelled sections A to J with their own repeat plan; played with every repeat it runs 224 bars, 448 quarter notes: 4:00 at q = 112, 3:33 at q = 126 | C, section script |
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
