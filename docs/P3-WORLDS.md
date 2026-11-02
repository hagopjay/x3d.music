# P3: the two worlds, live

Beethoven's *Ode to Joy* and Mozart's *Rondo alla Turca* as X3D worlds in X_ITE, driven by a page that owns the clock. Every thread, hole, pin, tooth and tile is a note of the score card, and nothing moves without one. This page says what was built, what was measured, what went wrong on the way and what is still unknown.

Grades: **C** a command or test showed it, **L** reasoned or read, **S** not checked.

## What exists

| Piece | World file | What is drawn | Size and budgets (C, `build/worlds/*.report.json`) |
|---|---|---|---|
| *Ode to Joy* | `build/worlds/ode.x3d` | A cathedral nave with a gantry loom. A tapestry of 256 by 384 cells; each statement of the theme lays its colours (indigo, silver, gold, then ivory with crimson), a row at the instant its statement reaches it, and a cell belongs to one note of that row (D-021). A card chain with one hole for each of the 3,101 notes. The rose window is the circle of fifths and flares with the chord. Light shafts lean with the harmonic tension. The shuttle flies for the tune, the batten beats on kick and snare, the harness lifts on the hat | 3.10 MB, 11 draw calls, 22,284 triangles, 5 shaders, 7,950 interpolator keys, 226 KB of event textures, 12 shots |
| *Rondo alla Turca* | `build/worlds/turca.x3d` | A domed hall. A barrel with 1,613 pins for the 2,810 written notes (a repeat reuses its pin), a steel comb of 51 teeth, a floor of 12 sectors by 5 rings (pitch class on the circle of fifths, octave by ring) and five clockwork players for the percussion: davul, cymbal, tom, triangle, jingle. Lanterns and flares | 3.67 MB, 30 draw calls, 60,686 triangles, 11 shaders, 5,769 keys, 160 KB of event textures, 56 shots |

The spec's budgets are 150 draw calls and 1.5 million triangles a world; both worlds are far under (C). The Turca file is over the 3 MB the spec hoped for and was left alone: the host takes 16 MB a file.

The page (`build/page`, 30.8 MB in 118 files, C `manifest.json`): X_ITE 16.5.1 as the page's own files (8.5 MB, 106 files), the two worlds, the masters as AAC in `.mp4` (14.7 MB), `data/<piece>.json` (the card's bars, tempo, passes, chords and a slim table of notes, 0.8 MB) and 0.05 MB of scripts (`clock.js`, `driver.js`, `ui.js`, `hover.js`, `boot.js`; no modules, no `eval`).

## How a world follows the score

- **The page owns the clock** (D-019). X_ITE has no `browser.currentTime`. The master is decoded into a Web Audio buffer and played from it; heard time comes from `getOutputTimestamp`; each frame the page sets `FractionBus.set_fraction`, and a ROUTE carries `SecondsBus` to every shader's `u_time`. There are no Script nodes.
- **An event is a texel.** Each thing that can light (a thread's row, a pin, a tooth, a tile, a chord) is a row of an event texture: sorted events of on-time, off-time, three bytes the shader may read and the card's note index. Times are 24-bit fractions of the scene's length, so a time resolves to about 13 microseconds (C, `test_worldlib.py`). A shader finds its events by binary search on `u_time` and nothing else.
- **The camera is a shot list** on the cut grammar (cuts on phrase downbeats, moves of whole bars, pace follows density; C, `test_worldlib.py`). The page's own camera is a second viewpoint, `Free` (D-020).
- **Score-true both ways** (C, `test_world_ode.py`, `test_world_turca.py`). Ode: every note is exactly one hole (hole *i* is note *i*), every weave owner is sounding at the moment its row is woven, and a row stays bare only when no note of its families sounds then. Turca: each written note is drawn once by a tile, a tooth and a pin, the pins are exactly the written heads, and every pin meets its tooth at its note's time to within 0.002 rad and 1 mm.

## What was measured (all C, on the files as built)

| Witness | Result | Tool |
|---|---|---|
| Unit tests | 69: meshes 14, shared world code 15, Ode 22, Turca 18 | `python3 -I -m pytest -q gen` |
| Grammar, Meaning, Traps | 2 files, 0 failed. The gate's heuristic `glsl-int-literal` warns 83 times (Ode) and 163 times (Turca); every shader compiles and links in X_ITE | `witnesses/gate_all.py`, validator 327c5c4, gate 21f5792 |
| Behaviour | 16 of 16 (8 a world): loads in 2.1 s (Ode) and 2.6 s (Turca) under software GL, every shader compiles (5 of 5, 11 of 11), every ROUTE fires and moves (41 ROUTEs from 16 fields, 46 from 19), the scene's clock equals the bus times the length exactly | `witnesses/behaviour.mjs` |
| Eyes (the program's part) | 12 stills a world at fixed score times: none black, none blown out, none flat. The picture judge and the owner's eye are the other two parts and are not in this number | `witnesses/eyes.mjs` |
| Page | 20 of 20: the splash and Play, the three views, Space, seek by bar, bar and beat and tempo arithmetic equal to the card on 60 notes a piece, the chord compass, the Ode's lines, the camera rig, calm, the end card with its credits | `witnesses/page_test.mjs` |
| Hover | 8 of 8: the page's copy of the weave's integer hash equals the shader's on 8 vectors; a thread, a hole, a pin, a floor tile and a lit tile each name the note the score card gives (id, bar and beat included); a thread not yet woven says when it will be | `witnesses/hover_test.mjs`, `witnesses/hover_expect.py` |
| Host | 10 of 10: each piece walked from 0 to its end in 110 steps (111 settings; the scene's clock followed the page's to 1.1 microseconds on the Ode and 5.4 on the Turca), the end card came up, 14 requests all answered 200, 0 policy violations beyond the known harmless ones, the real audio clock decoded the `.mp4` and ran in step with the page's | `witnesses/host.mjs`, under a copy of the host's policy (C for the copy, L for the real host) |
| Reproducible | a rebuild gives the same sha256 for all six outputs, on this machine | `receipts/p3-worlds.json` |

Silent crossings (C, `test_world_turca.py`): a pin meets a tooth with no note under it twice in the whole piece, at 174.583 and 174.643 s. They are the pickup graces of the second ending, whose pins sit on a band the first statement of that section turns past too (D-025). The barrel changes band 12 times and always in silence (the shortest slide is 60 ms).

## What went wrong on the way

- **A comb attribute tiled to 84 components.** `FloatVertexAttribute` allows four; the fork's schema check named `numComponents='84'`. `Mesh.with_attr` is now strict about shapes and has tests (C).
- **The Behaviour witness's first reads were wrong.** `getField` is deprecated and `addFieldCallback` takes the key first; the shipped Clock is disabled, so its `fraction_changed` is silent until the witness enables it for a moment; and the Turca's left arms never moved (`Band_*_armL_rot`) until they were driven from real events (a test now holds it).
- **Harmless failures needed names.** X_ITE cancels the world request after the server has answered 200 (`net::ERR_ABORTED`); its own interface font is refused by the policy copy; its tangent generator's WebAssembly will not compile under it. None is used by the page; the Host witness classifies them by the server's own log and counts everything else as blocked (D-024).
- **The page's first rig was bound to the first piece.** A grab on the Turca did nothing; the rig is now single and reset per piece. Lyrics and compass text outlived a piece switch and the corner card showed behind the splash; both fixed and tested.
- **The tapestry could not be pointed at.** X_ITE picks on the GPU, so a faint light shaft in front of the tapestry hid it from the pointer. `Shape.pointerEvents` lets the pointer through, but it is X3D 4.1 and the worlds are 4.0, so the worlds name their effect shapes (`Fx_Shafts`, `Fx_Halo`, `Fx_Flares`) and the page sets the field by SAI (D-022).

## Still unknown (S unless marked)

- **How it runs on a real GPU.** Every frame here is software-drawn (SwiftShader, about 0.6 s a frame); no frame rate is quoted anywhere. The Fps witness needs a real GPU.
- **How it sounds and how it looks to a person.** The masters are set by meters, and the picture judge and the owner's eye have not seen these frames before the first stop-and-show.
- **The real host's policy.** The Host witness runs a copy written from the Artifact page contract (C for the copy, L for the host). WebAssembly, blob workers and AAC decode on the real host are unchecked.
- **Safari and Firefox,** and audio latency on real devices (the Sync witness).
- **Flashes.** The Flash witness (no harmful flashes) is not written yet; the Turca's lit tiles and the Ode's rose are the places to look.
- **The Ode's picture is a procedural stand-in** (the spark over a landscape with linked silhouettes, drawn in `gen/picture_ode.py`). The generated picture comes in P4 and will be labelled AI-made.

## Rebuild and re-check

```
python3 -I tools/fetch_xite.py                                  # X_ITE 16.5.1, sha512 checked, into build/xite
python3 -I gen/world_ode.py && python3 -I gen/world_turca.py    # build/worlds/<piece>.x3d, .map.json, .report.json
python3 -I -m pytest -q gen                                     # 69 tests
X3D_MCP=<validator> LOOM_GATE=<gate tools> python3 -I witnesses/gate_all.py build/worlds
python3 -I page/build_page.py [--no-audio]                      # build/page (the masters are encoded from build/audio when present)
node witnesses/behaviour.mjs --world build/worlds/ode.x3d       # and turca
node witnesses/eyes.mjs --world build/worlds/ode.x3d --out build/stills/eyes-ode
node witnesses/page_test.mjs && node witnesses/hover_test.mjs && node witnesses/host.mjs
python3 -I witnesses/receipts.py check receipts/p3-worlds.json
```

CI runs all of it in the `page` job, after the audio job has rendered the masters and encoded them.
