# P0 probe report

Run 2 Nov 2026 on the build branch. Every line carries a grade: **C** confirmed by a command whose output is kept (`docs/p0/probes.json`, the receipts, or the tool named), **L** likely (read from a reference or inferred), **S** suspected (not measured). Every number names the tool and version behind it.

**Measuring setup (C).** Chrome for Testing 153.0.8010.12, headless, driven by Playwright 1.63.0, on software GL (ANGLE over SwiftShader, WebGL 2.0, GLSL ES 3.00, no GPU). X_ITE 16.5.1 from the pinned npm tarball (sha512 in `tools/pins.json`). Pages are served by `witnesses/harness.mjs` from a skeleton like the host's with a strict Content-Security-Policy copy: scripts from the page itself, inline and five named CDNs, fetches only from the page itself, no `unsafe-eval`. The real host's policy is not visible from the build sandbox, so every "under the copy" result is C for the copy and S for the host. Validator: `x3d_mcp` fork at `327c5c4`; gate: `x3d.onto` at `21f5792`. ffmpeg 6.1.1 made the audio files. Re-run: `node witnesses/probes.mjs --strict` after `python3 -I tools/fetch_xite.py` and `python3 -I gen/probes/make_probes.py`.

## Summary

| # | Question | Answer | Grade | What it changes |
|---|---|---|---|---|
| 1 | Does the time bus (FractionBus to SecondsBus to a shader's `u_time`) drive a shader in X_ITE 16.5.1? | Yes. `u_time` equals fraction x 230 s to 1.4e-14 s over 32 settings | C | Nothing: the design stands |
| 2 | Do per-vertex attributes reach the shader (`FloatVertexAttribute`, a `flat` varying)? | Yes. 768 pixel checks, 0 mismatches at 1 ms either side of every threshold | C | Nothing |
| 3 | Does an 8-bit RGBA `PixelTexture` carry a 16-bit time exactly, with nearest filtering and no mipmaps? | Yes. 0 mismatches either side of every threshold; the blue channel read 0.45 texel off centre is exactly 0 or 255 | C | Nothing. One count is 3.5 ms at a 230 s piece; the shader allows 4 ms slack |
| 4 | Does Web Audio decode the `.mp4` master, and does it shift onsets? | Yes. AAC `.mp4`, Opus `.ogg`, `.mp3` and `.wav` all decode; bursts at 1.000 s and 2.000 s shift 0.000 ms against the wav | C Chrome 153; S other browsers | Ship AAC `.mp4` only (D-005) |
| 5 | Does the audio clock track the page clock? | Yes in headless Chrome: slope 0.9996 to 0.9999 over 2.5 s, residual at most 5 ms (one frame is 16.7 ms) | C headless; S real devices | Read `outputLatency` at run time; Sync stays at one frame |
| 6 | Do 4.1 `GaussianSplats` draw in X_ITE 16.5.1? | Yes, if the policy allows WebAssembly compile. Under the strict copy the splat sorter is refused and the page stays on its loading splash | C under the copy; S on the host | A host self-test decides (D-004) |
| 7 | What happens to a 4.0-declared file that uses `GaussianSplats`? | X_ITE refuses it, the validator refuses it, and the new `version-fits-nodes` rule flags it | C | Three witnesses agree |
| 8 | Do Grammar, Meaning, Traps and Receipts pass the probe worlds, and does the gate catch a bad one? | Yes to both (section G) | C | Nothing |
| 9 | Can the first-choice video model be called? | No: it is reachable only through a newer API, and that API refuses this project | C | Fallback (D-006) |
| 10 | Can the fallback video family be called? | Access yes (it answers parameter checks); no paid call was made | C access, S output | First draft at the start of P4 |

## A. Time bus, per-vertex attributes, event data texture

`probe_a.x3d` (X3D 4.0, Interchange plus explicit components): eight strips, each carrying a per-vertex onset time (`a_tOn`) and an index (`a_k`) as `FloatVertexAttribute`s, plus an 8 x 1 `PixelTexture` whose red and green bytes hold each strip's onset as a 16-bit fraction of 230 s. The fragment shader writes red = lit by the attribute, green = lit by the texture (with 4 ms slack), blue = the texture read 0.45 texel off centre. A `ScalarInterpolator` pair (`FractionBus`, `SecondsBus`) turns a fraction into seconds for `u_time`. The probe sets the fraction, waits four frames, screenshots 640 x 360, decodes the PNG and reads three points in each strip. 32 settings: four whole-scene fractions (0, 0.3, 0.6, 1.0) and, for each of seven strips, 1 ms before and after both thresholds. Stills: [0.30](p0/probe_a_f0.30.png), [1.00](p0/probe_a_f1.00.png) (strips 0 to 2 lit at 0.30; blue alternation is the parity read through the texture).

| Id | Claim | Observed | Grade |
|---|---|---|---|
| A0 | The shader links with `data:` ShaderParts, GLSL ES 3.00 `in`/`out`, a `flat` varying, `texelFetch` and per-vertex attributes | `ComposedShader.isValid` true | C |
| A1 | `u_time` equals fraction x 230 s | max error 1.4e-14 s over 32 settings | C |
| A2 | A strip lights from its attribute within 1 ms of the exact time | 768 pixel checks, 0 mismatches | C |
| A3 | A strip lights from the texture's 16-bit time within the 4 ms slack, both sides of every threshold | 0 mismatches | C |
| A4 | The texture is read with nearest filtering and unchanged colour | blue exactly 0 or 255 at all pixels | C |

Software GL says nothing about frame rate (S until the Fps witness runs on a real GPU).

## C. Audio

`click.*`: a stereo 48 kHz file with two 10 ms bursts at exactly 1.000 s and 2.000 s, encoded by ffmpeg 6.1.1 to AAC in `.mp4` (256 kb/s), Opus in `.ogg` (192 kb/s) and `.mp3` (256 kb/s). Each is fetched under the policy copy and decoded with `decodeAudioData`; onset = first sample above 0.05.

| Id | Claim | Observed | Grade |
|---|---|---|---|
| C1 | The wav decodes; bursts at 1.000 s and 2.000 s | onsets 1.00084 s and 2.00084 s (0.84 ms is the burst's own fade-in); the context resamples to 44.1 kHz; duration 2.49998 s | C |
| C-mp4 | AAC `.mp4` decodes with no onset shift | shift 0.000 ms and 0.000 ms against the wav | C |
| C-ogg | Opus `.ogg` decodes with no onset shift | 0.000 ms, 0.000 ms | C |
| C-mp3 | `.mp3` decodes with no onset shift | 0.000 ms, 0.000 ms | C |
| C5 | The `AudioContext` runs and its clock advances at 1.000 +/- 0.001 of `performance.now()` | state running; slope 0.9996 to 0.9999 over 2.5 s in five runs; **one CI run read 0.998667 over 2.5 s** (the page-facing C6 read 1.000000 in the same run), so the probe now fits over 8 s with the same tolerance (D-027) | C headless |
| C6 | `getOutputTimestamp()` maps context time to performance time with slope 1 | slope 0.99996 to 1.000003; residual 0.1 to 2 ms | C headless |

`canPlayType` answers "probably" for `.mp4` AAC, `.ogg` Opus and `.mp3` (C, Chrome 153). `outputLatency` reads 32 ms and `baseLatency` 10 ms with no audio device, so those numbers are the headless defaults, not a real device's (S). Safari and Firefox were not run (S): AAC `.mp4` is the choice every current browser plays (L).

## D. 4.1 splats under the policy copy

`probe_splat41.x3d`: 27 splats on a 3 x 3 x 3 lattice, `bboxSize` and `bboxCenter` set, spherical-harmonic degree-0 colour, declared X3D 4.1, Immersive, component `GaussianSplats` level 1. Each run uses a fresh page.

| Id | Claim | Observed | Grade |
|---|---|---|---|
| D1 | With `'wasm-unsafe-eval'` allowed, X_ITE 16.5.1 makes a `GaussianSplats` node from the 4.1 file and draws it | node type `GaussianSplats`, version 4.1; 96 of 576 grid points lit, 53 colour cells ([render](p0/splat_wasm_probe_splat41.png)) | C |
| D2 | Under the strict copy (no WebAssembly compile) the splats do not draw | the sorter worker fails: "Compiling or instantiating WebAssembly module violates the following Content Security policy directive"; the scene did not become current in 25 s and the page stays on the loading splash ([screenshot](p0/splat_strict_probe_splat41.png)) | C under the copy |
| D3 | The same node in a file declared 4.0, wasm allowed | X_ITE: "XML Parser: Unknown node type 'GaussianSplats'. You probably have insufficient component/profile statements and/or an inappropriate specification version."; no node, nothing drawn | C |

The real host's policy decides whether D2 applies to the published page (S). `D-004` plans both outcomes. The films are unaffected: they render locally with no policy.

Known-harmless under the copy (L, listed so they are not mistaken for faults): X_ITE's own interface font (three `font-src` blocks) and its tangent generator's WebAssembly (one `script-src` block); the page does not use X_ITE's interface or normal-mapped tangents.

## G. Grammar, Meaning, Traps, Receipts on the probe worlds

`python3 -I witnesses/gate_all.py build/probes` (validator `327c5c4` with its XSD, 23 semantic checks and profile check; gate `21f5792`; the five Loomsong rules):

| File | Result | Grade |
|---|---|---|
| `probe_a.x3d` | clean: XSD valid, 0 semantic errors, profile OK, 0 gate and rule hits | C |
| `probe_splat41.x3d` | clean | C |
| `probe_splat40_bad.x3d` (4.0 with `GaussianSplats`, red on purpose) | red on `fork-xsd` (the validator's component list has no `GaussianSplats` at 4.0) and on `version-fits-nodes`; the gate fails if either goes quiet | C |

The validator also earned its place on the first draft: `probe_a.x3d` declared Navigation level 2 for an `OrthoViewpoint`, and the profile check named the node, the line and the fix (level 3). X_ITE had drawn it anyway. That is "valid is not the same as visible" in the other direction, and why both witnesses run (C, validator `327c5c4`).

Receipts: `witnesses/receipts.py check receipts/p0-probes.json` rebuilds the probe worlds and gets the same sha256 for all five outputs (C, Python 3.13).

## E. Video models

| Id | Claim | Observed | Grade |
|---|---|---|---|
| E1 | The preview video model (both versions listed) can be called with a plain generate request | No: HTTP 400 "<model> is only supported in the Interactions API and cannot be called directly via generateContent." for both versions; error responses do not bill | C, API call 2 Nov 01:48Z; billing L |
| E2 | The Interactions API accepts this project | No: the typed create method answers HTTP 400 `RESOURCE_PROJECT_INVALID` ("Invalid resource field value in the request") in the global, regional and multi-region locations, with the project's identifier and its number, and also for a plain text model as a control, so the video request is not the cause | C |
| E3 | The HTTP-body variant of that method works | No: HTTP 501 `UNIMPLEMENTED` in two locations | C |
| E4 | What the API schema says about video output | The discovery document (revision 20261027) gives the Interactions API a `background` flag and a video response format with aspect ratio 16:9 or 9:16, duration, resolution 360p to 4k, and delivery inline or by storage URI | C, discovery document |
| E5 | The second video family can be reached from this project | Yes: three model versions answer a parameter check (HTTP 400 "Invalid aspect ratio") on the long-running predict method, so access exists; jobs are polled, which sidesteps the proxy's 30-second cut | C access; the output is S until a draft is made |

No paid call was made in P0. If the project owner enables the newer API for the project, E2 flips and the first-choice model can be tried again with the shape in E4 (D-006).

## F. The worlds in X_ITE 16.5.1 (P3, headless Chrome, software GL)

| Id | Claim | Observed | Grade |
|---|---|---|---|
| F1 | A page can read a world's ROUTEs and watch every source field through SAI | Yes: `scene.routes` lists `sourceNode`, `sourceField`, `destinationNode`, `destinationField`; `node.addFieldCallback(key, field, fn)` takes the key first, and `getField` is deprecated (a console warning) | C, Behaviour witness |
| F2 | A `Viewpoint` can be offset from the page | No: it has no `positionOffset` or `orientationOffset`. A second viewpoint (`Free`) that the page places and binds works, and binding `Cam` again returns to the directed track | C, page test |
| F3 | A page can read a `PixelTexture` back | Yes: `image` gives `width`, `height`, `comp` and an `array` of one 0xRRGGBBAA integer a pixel, so hover reads the tapestry's cells from the world itself | C, hover test |
| F4 | A TouchSensor reports a hit through any shape in front of it | No: X_ITE picks on the GPU, so every shape with `pointerEvents` true hides it. With the Ode's light shafts in the scene `HoverTap` reported nothing; with them removed it reported hits on the tapestry plane (z = -23.8). Setting `Shape.pointerEvents = false` by SAI on the effect shapes lets the pointer through. The field is in the 4.1 schema only | C, `witnesses/hover_test.mjs`, a scratch run before and after, the 4.1 schema |
| F5 | One `<x3d-canvas>` can change worlds | Yes: `X3D.getBrowser(el).loadURL(new X3D.MFString(url))`; the page keeps one canvas and one rig | C, page test |
| F6 | X_ITE asks for nothing the host would refuse | With `splashScreen`, `contextMenu`, `notifications` and `timings` set to "false" the stepped Host run made 14 requests, all answered 200. Three harmless cases remain: the cancelled world request after a 200 (`net::ERR_ABORTED`), its interface font if the attributes are left on, and its tangent generator's WebAssembly, which will not compile under the strict policy copy and which the page does not use | C, Host witness |
| F7 | The Web Audio clock reads in headless Chrome | Yes: `getOutputTimestamp` gives a usable pair; the context reported 44.1 kHz, a base latency of 0.010 s and an output latency of 0.032 s. The master decodes from the `.mp4` and the page's clock advanced 7.835 s while the audio clock advanced 7.835 s | C in headless Chrome, S on real devices |
| F8 | A frame costs | About 0.6 s in software GL at 1280 by 720, so no frame rate is quoted | C for the figure |
| F9 | A pose set on a bound `Viewpoint` shows at once | Without a bind, yes: the pick under the camera was exactly under it in 4 of 4 floor looks. Re-sending `set_bind = true` to the same, already bound, viewpoint starts the `NavigationInfo` transition (X3D's default is one second, LINEAR; the worlds keep it) and the pointer's pick reads the old pose until it ends: with `transitionType` TELEPORT it was exact in 4 of 4 as well. The page's rig binds once per grab, so it is not affected (D-028) | C, a scratch script of four floor looks in three variants |
| F10 | A host's content policy can be read from inside the page | Yes, to the extent the page can try: `page/report.js` compiles an empty WebAssembly module, starts a blob worker and listens for `securitypolicyviolation`, and writes the answers to the page's own store (D-029). Under the strict policy copy it read `CompileError` for WebAssembly, `ok` for the blob worker and two `script-src` refusals (the probe's and X_ITE's tangent generator's). The real host's answers arrive when the preview is opened there | C under the copy, S for the host |

## H. Generated media in the worlds (P4)

| Id | Claim | Observed | Grade |
|---|---|---|---|
| H1 | The second video family makes the clips the spec asks for | Yes: image-to-video and text-to-video, 8 s, 16:9, video only. Drafts at 720p took 64 to 79 s each and are 3.2 to 12.3 MB; four finals at 1080p took 113 to 132 s each and are 26.8 to 35.8 MB (too big for a page: `tools/prep_cards.py` re-encodes each to 3 to 6 MB at 1600 px wide, H.264, no sound) | C, the files and the private run ledger |
| H2 | A generated clip of a still room can be given camera poses (the Pose witness) | Yes, all three backdrops: COLMAP with sequential matching, an overlap of 12 and the initial triangulation angle lowered to 3 degrees (a slow dolly has little parallax; the default was not compared) registered 48 of 48 sampled frames in the best model each time (it found two models in the first and the third); mean reprojection error 0.57, 0.48 and 0.55 px; median point error 0.455, 0.379 and 0.412 px; 30,251, 20,485 and 8,659 points. The spec's bars are 90 % registered and under 1 px | C, private run logs; the bars met |
| H3 | Whether the clips become photoreal splat worlds | Not known: training and the Fidelity witness (PSNR at least 22 dB, SSIM at least 0.75 on held-out frames) need the GPU machine, which is stopped (D-038). The training input is built and uploaded | S |
| H4 | Where an `ImageTexture`'s first row is in X_ITE 16.5.1 | At texture coordinate v = 0, the opposite of the X3D text: the dome's first atlas lookup showed the top and bottom rows of motifs swapped until the lookup counted rows from the top (D-033) | C, the Atlas witness, with a mutation check |
| H5 | A shader can tell that its picture has not arrived | Yes: an `ImageTexture` that has not loaded or has failed reads as alpha 0 in a custom shader; the dome keeps its procedural tiles for any texel whose alpha is not 1, and with the picture missing the world is still lit, the only thing the console reports being the failed request | C, the Atlas witness |
| H6 | A mirrored lookup into a 4 by 3 atlas puts each motif on screen as it is in the file | Yes under mipmaps and anisotropy 8: on a 7 by 7 grid of small windows the twelve cells differ from their own tiles by 2.2 of 255 on average (worst tile 4.6), against 9.2 flipped top to bottom, 4.1 flipped left to right (many motifs are mirror symmetric) and 9.0 turned half way; the worst cell is at 0.10 of the nearest other motif's difference | C, the Atlas witness (it needs worst tile under 22, identity under 0.5, orientation under 0.5) |
| H7 | A custom shader can sample an `ImageTexture` under the strict policy copy | Yes: the picture is served from the page's own files (img-src 'self'), 200, no violation | C, Atlas, Behaviour, Host |
| H8 | A muted `<video>` with a poster plays under the strict policy copy (media-src 'self') and the music does not wait for it | Yes in headless Chrome: the title card reached ready state 4 and played, an opening covered the world while the clock ran, and with the video files withheld the poster showed and only the failed requests were reported. The real host's behaviour is read from the preview's report (`cards` in `reports/<id>`) | C under the copy, S on the real host |
| H9 | Re-encoding strips a generated clip's metadata | Yes, in two steps: the encode drops every tag of the source and every SEI unit (the encoder's settings line is one), then a copy into a fresh container drops the encoder string the encoder writes into its own stream. The originals carry an encoder string of their maker; a card carries the container's own brand and handler names and our one comment ("AI-made: ..."), and nothing else (a first attempt with the encoder's own flags left both the string and the settings line; the test now looks for them). The posters are rebuilt from pixels and pass the sweep's image rule | C, `ffprobe`, `strings`, `witnesses/test_cards_media.py` |

## I. The private preview on a real machine (P3's page, one report read on 5 Nov 2026)

The preview of 2 Nov (the P3 page: no generated pictures, no cards) wrote one report on 3 Nov when it was opened. It is one machine, one window and one session, so each line says which.

| Id | Question | Observed | Grade |
|---|---|---|---|
| I1 | Does the real host let WebAssembly compile and blob workers run? | Yes: both read ok; the report lists no policy violation and no page error | C, one report |
| I2 | Does the page hold a frame rate on a real GPU? | On Windows with Chrome 156 and an Intel UHD 620 integrated GPU (ANGLE over Direct3D 11), in a window of 1105 by 576 at a device pixel ratio of 1.1: the Ode played 42 s at a median 59.7 frames a second (1 % low 58.8, none over 33 ms), the Turca 73.2 s at a median 59.7 (1 % low 58.0, 2 of 4,363 frames over 33 ms, none over 50 ms); X_ITE's own meter read 58.8 | C for that machine and window; S for a larger window or another machine |
| I3 | Does the AAC master decode and the audio clock run there? | Yes: mode `webaudio`, state running, 48,000 Hz, base latency 10 ms, output latency 48 ms; the decoded buffers are 215.877 s and 218.857 s, the masters' lengths | C, one report |
| I4 | How long until a piece is ready? | 4.4 s (Ode) and 4.8 s (Turca) after it was asked for | C, one report |
| I5 | What did this report not see? | The generated pictures, the dome's atlas and the cards (the page it read predates them), Safari, Firefox, a phone, and how it sounds and looks to a person | S |

## Still S after P0

- Decode and playback in Safari and Firefox; audio latency on real devices.
- Frame rate on other machines and in a larger window (one real report is in section I; the Fps witness proper needs a defined machine).
- The real host's policy for a *new* thing: WebAssembly compile, blob workers, AAC decode and WebGL2 are answered by section I; video playback in the cards is not (the preview must be opened with them).
- X_ITE splat budgets at scale (1.5 M splats per world): P4. Draw calls and triangles were measured in P3 and both worlds are far under (`P3-WORLDS.md`).
- The output of the fallback video family.
