# P4: generated media in the worlds

Pictures and moving pictures made by generative tools, brought into the two worlds and the page without ever touching the music: the Ode's tapestry is woven from a generated picture, the Turca's dome is tiled with twelve generated Iznik motifs, and four animated cards frame the pieces. Everything is labelled AI-made where it appears, every prompt is in `docs/PROMPTS.md`, and every world still builds and passes its witnesses without any of it. This page says what was built, what was measured, what went wrong on the way and what is still unknown.

Grades: **C** a command or test showed it, **L** reasoned or read, **S** not checked.

## State

| Part | State |
|---|---|
| Pictures in the worlds | In. The Ode's tapestry picture (`art/ode-tapestry.png`) and the Turca's dome atlas (`art/dome-motifs.jpg`) are chosen (the first tapestry candidate, motifs A to L), woven or tiled by the generators, and labelled AI-made in the corner note and the credits. The owner has not marked the drafts page yet, so the picks are mine and are one command to change (`tools/prep_art.py --tapestry tapestry-cand-N`) |
| Animated cards | In the page: a picture behind the title card, an opening over each piece, a picture behind the end card. The four finals (1080p) are re-encoded to 3 to 6 MB each and are not in this repository (`tools/prep_cards.py`). The credits and bumper stills have drafts only |
| Backdrops as 3D worlds | Not in a world. The three clips pass the Pose witness; photoreal splats and the Fidelity witness need the stopped GPU machine, which waits for the owner's typed yes (D-038) |
| Further paid generation | Stopped. The owner cut the spending cap below what had already been spent (5 Nov), so the credits and bumper clips, the other finals for the backdrops and the GPU training are not made (D-040) |
| Prompts and labels | `docs/PROMPTS.md`: 29 rows, each with the sha256 of the prompt as sent, the label shown with the result, the ledger run id and what became of it |

## What was built

- **The art switch** (D-030). `art/manifest.json`, `gen/artlib.py`. A picture whose file is missing or whose sha256 differs is never used; `LOOM_ART=procedural` builds the stand-ins; CI builds and tests both.
- **The Ode's tapestry** (D-031). `gen/picture_ode.py`: the generated picture is fitted, cell by cell, to the nearest of the five threads in linear light, so it is still woven from threads that each belong to a note of their row; two crimson border threads frame it. 12 unit tests (`gen/test_picture_ode.py`) plus the Ode world's 22. With the generated picture every cell of indigo, silver, gold and ivory has an owner (100 % woven each); the two crimson border threads are laid only in the 204 of 384 rows that have a crimson note, so the frame is broken where there is none (C, `gen/test_world_ode.py`).
- **The Turca's dome** (D-032, D-033). `gen/shaders/motif_lib.glsl`, `dome_fs.glsl`: tile *t* of a 4 by 3 atlas with mirrored gutters, picked by the dome's section (A to H one each, I and its returns one, J one), the hush before the first note and the final chord on their own tiles; the dome keeps its own procedural tiles for any texel that is not there yet.
- **Cards** (D-036). `page/cards.js`, `tools/prep_cards.py`, `witnesses/cards_test.mjs`, `witnesses/test_cards_media.py`.
- **Images carry nothing but pixels** (D-035). `tools/prep_art.py` rebuilds each picture from its raw pixels; the leak sweep reads the structure of every PNG and JPEG.
- **The report** now says, for a build with cards, whether the host played the cards' video (`cards` in `reports/<id>`).

## What was measured (all C, on the files as built)

| Witness | Result | Tool |
|---|---|---|
| Unit tests | 81 generator tests (meshes 14, shared world code 15, the Ode's picture 12, the Ode world 22, the Turca world 18) and 28 witness tests (leak sweep 14, trap rules 9, card media 5) | `pytest -q gen`, `pytest -q witnesses` |
| Grammar, Meaning, Traps | both worlds and both stand-in worlds: 4 files, 0 failed (the gate's `glsl-int-literal` heuristic warns 83 and 163 times as before) | `witnesses/gate_all.py` |
| Behaviour | 16 of 16 on the worlds with their pictures and 16 of 16 on the stand-ins | `witnesses/behaviour.mjs` |
| Eyes (the program's part) | 12 stills a world, none black, none blown out, on the worlds with their pictures and on the stand-ins | `witnesses/eyes.mjs` |
| Atlas | 9 of 9: each of the twelve motifs reaches the screen as it is in the file (mean difference 2.2 of 255, worst tile 4.6, against 9.2 for the file flipped top to bottom and 9.0 turned half way), the dome draws with and without its picture, and the missing picture is the only thing the console reports | `witnesses/atlas_test.mjs` |
| Page | 20 of 20; the end card's AI statement now follows what the build says is AI-made | `witnesses/page_test.mjs` |
| Hover | 8 of 8; a card shows the score card's own bar and beat (D-037) | `witnesses/hover_test.mjs` |
| Report | 18 of 18 | `witnesses/report_test.mjs` |
| Cards | 23 of 23 with the test patterns: off under the test clock unless asked, a muted looping video behind the title, the clock never waits for an opening, an opening covers the world with the piece's name and dissolves on its own timer, once only, Escape ends one early, Calm leaves it out, the end card has its picture, the words say what is AI-made and never call a test pattern that, and with the video files withheld the poster shows and only the failed requests are reported | `witnesses/cards_test.mjs` |
| Host | 10 of 10 | `witnesses/host.mjs` |
| Leak sweep | 0 hits over every file | `witnesses/leak_sweep.py` |
| Receipt | a rebuild gives the same sha256 for all seven outputs on this machine: the Ode `b43ad7c0...`, the Turca `64f6f459...` (D-039) | `receipts/p4-worlds.json` |

The dome with its picture is much darker than the dome without it. The Atlas witness's frame of section D (from the floor, looking up, at 63.8 s) has a mean luminance of 0.120 and a 95th percentile of 0.391 with the picture, against 0.616 and 0.827 with the picture withheld, when the dome shows its own procedural tiles (C). That section's tile is a deep navy with silver tracery, and the dome's tint, darkest toward the zenith (`gen/shaders/dome_fs.glsl`), sits on top of it, which is the likely cause (L). It is not a fault and the floor the Eyes witness holds (nothing black, nothing blown out) is met, but it is the first thing a person will notice and the first thing for the owner to judge: another motif or a brighter tint is a small change, and whether the dark dome is better is not known (S).

## What went wrong on the way

- **The dome showed the wrong motifs on its top and bottom rows.** X_ITE 16.5.1 reads an `ImageTexture`'s top row at v = 0. A witness that asks "is it lit?" would never have noticed; the Atlas witness compares each cell with the file, and a mutation (the old row order) turns it red (D-033).
- **The Loomsong trap `data-texture-nearest` flagged the atlas.** A picture a shader filters is not data; the rule now exempts `Pic_` pictures and nothing else (D-034).
- **A hover check on the Ode's tapestry went red on a different picture.** The helper that gives the test its expectation had worked a note's bar and beat out again from the card's six-decimal seconds, and a choir note that sits on a bar line came out one bar early. The page and the card agreed; the test's arithmetic did not (D-037).
- **The page's end-card test assumed the Turca had nothing AI-made in it.** It now reads what the build says.
- **The first re-encode of the cards still carried the encoder's name and its settings line.** The flags that were meant to drop them did not; a two-step encode does, and a test looks for the strings (PROBES H9).
- **A session may not start the GPU machine.** The harness refused the start of the stopped L4 as a change to a shared resource; it was not retried, and the owner was asked to type a yes (D-038).
- **The first-choice video model is unreachable from this project** (PROBES E), so every clip is from the second family; nothing in the build depends on which.

## Still unknown (S unless marked)

- **How the AI worlds look to a person.** The owner has not marked the drafts page; the picture judge's flags were answered, his eye is the judge of record.
- **Photoreal splats.** Training and the Fidelity witness wait for the GPU machine (D-038). The dust stand-in is graded for what it is.
- **Whether the real host plays the cards' video.** The one report read so far (3 Nov, PROBES I) is of the earlier page without cards: it says WebAssembly and blob workers are allowed and the page held about 60 frames a second on an integrated GPU, which the cards and the dome's atlas add to. The new preview's report will say (`cards`, `env`, `play` in `reports/<id>`). A card that does not play shows its poster and costs nothing else (C, Cards test).
- **Whether autoplay of a muted video is allowed on every phone and in every browser.** Safari and Firefox are not checked (S).
- **The licence of `art/`.** CC BY 4.0 is a default in NOTICE.md; it is the owner's to change.

## Rebuild and re-check

```
python3 -I tools/prep_art.py --src <folder of generated pictures>        # art/: the tapestry's picture, the dome atlas, the manifest (the generated pictures are kept privately)
python3 -I tools/prep_cards.py --src <folder of generated clips>         # build/media: the four cards and their posters (or --synthetic for the CI test patterns)
python3 -I gen/world_ode.py && python3 -I gen/world_turca.py             # build/worlds, with art/ beside them where a world names it
LOOM_ART=procedural python3 -I gen/world_ode.py --out build/worlds-standin    # and turca: the stand-ins
python3 -I gen/probes/make_atlas_probe.py && node witnesses/atlas_test.mjs
python3 -I witnesses/receipts.py check receipts/p4-worlds.json            # the worlds rebuild to the same bytes
python3 -I page/build_page.py --no-audio [--media <folder>]               # build/page, with the cards in build/media or the folder named
node witnesses/cards_test.mjs && node witnesses/page_test.mjs && node witnesses/hover_test.mjs
python3 -I -m pytest -q gen witnesses/test_cards_media.py
```

CI runs all of it in the `page` job with the test patterns in place of the animated pictures.
