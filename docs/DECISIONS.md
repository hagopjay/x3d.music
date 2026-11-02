# Decisions

One entry per decision that changes what gets built, newest last. Each says what was decided, why, and how to undo it. A decision that depends on something unmeasured says so.

## D-001 (2 Nov 2026) What the public repository holds

Code, docs, score cards, receipts and run records go in. Media over 5 MB, spend figures, keys, cloud project identifiers, run-as identities, private links and the names of AI vendors and models never do; the leak sweep (`witnesses/leak_sweep.py`) runs in CI on every push and a hit fails the build. AI-made images, video and voice are labelled as such wherever they appear.
*Why:* the repository is public by its owner's choice, and a leak cannot be taken back once pushed. *Undo:* only the owner can widen it, in words.

## D-002 (2 Nov 2026) Every tool a receipt names is pinned

`tools/pins.json` fixes the validator and the gate by commit, X_ITE by version and sha512, the browser and its driver by version. A pin changes in its own commit, with the reason in the message. The validator's tag `loom-pin-2026-11-01` does not exist yet; the commit it should point at is pinned instead and the tag is requested from the owner.
*Why:* "valid" and "renders" mean nothing without the name of the checker and the browser behind them.

## D-003 (2 Nov 2026) The five trap rules live here first

`witnesses/loomsong_rules.py` holds `bus-wired`, `data-texture-nearest`, `splat-bbox`, `movie-not-still` and `version-fits-nodes`, each with one passing and one failing test. They go to the Loom gate's own repository by pull request, not straight into main; until then CI runs them beside the gate.
*Why:* the gate's repository is not writable from this build, and the spec asks for review before a rule enters it.

## D-004 (2 Nov 2026) Splat backdrops on the page wait for a host measurement

X_ITE 16.5.1's splat sorter is WebAssembly. Under the policy copy without WebAssembly compile it fails and the scene never finishes loading (PROBES.md, D2). Whether the real host allows it is not known from the build sandbox. The first page the owner opens carries a host self-test that reports what the host allows (WebAssembly compile, blob workers, AAC decode, WebGL2) and the result decides the splat backdrops:
- allowed: splat backdrops stay on the page as the spec says;
- refused: the page shows the same backdrops as pre-rendered motion layers, and the splats are used where there is no policy: the films.
*Why:* find out before building on it; both outcomes are planned for. *Undo:* none needed.

## D-005 (2 Nov 2026) The page ships AAC in `.mp4` only

AAC `.mp4`, Opus `.ogg`, `.mp3` and `.wav` all decode in Chrome 153 with no onset shift (PROBES.md, C-mp4 to C-mp3). AAC is the one every current browser plays, so it is the one shipped; the others are not built.
*Why:* one file, one codec, less to verify. *Caveat:* decoding was measured in Chrome only (S for Safari and Firefox).

## D-006 (2 Nov 2026) Video for the splat backdrops comes from the second video family

The preview video model named in the spec as the first choice is reachable only through a newer interaction API, and that API refuses this project, even for a plain text request (PROBES.md, E1 to E3). The spec's fallback is used: the second video family, which this project can reach, is polled as a long-running job, so the proxy's 30-second cut does not matter. No paid call was made in P0.
*Why:* a measured refusal, with the fallback already costed in the spec. *Undo:* if the owner enables the newer API for the project, the first model can be tried again at no change to the pipeline: only the request shape differs.

## D-007 (2 Nov 2026) Receipts for generated files

`witnesses/receipts.py` records the command, the inputs' and outputs' sha256 and sizes, and a check rebuilds and compares. The Loom's own `loom_receipt.py` stays for Blender-made assets. Audio probe files are not receipted (their bytes depend on the encoder build); the masters' receipts will record the tool versions beside the hashes.

## D-008 (2 Nov 2026) Note ids: the last digit is the rep

`<piece>.<section><rep>.<instrument>.<voice>.<counter>` with a single-digit rep, so `turca.I11...` is the first ending (section `I1`, first pass) and `turca.I2...` is section `I` in its second pass. The two can never collide because the rep is always the last character of that part.
*Why:* the kern file names its endings `I1` and `I2`, which would clash with "section I, rep 1 and 2" in the spec's id format. *Undo:* rename the endings (for example `Ea`, `Eb`) in `score/turca.py` and rebuild.

## D-009 (2 Nov 2026) Bars are counted on the performed grid; the file's numbers are kept beside them

Bar 0 is the Turca's upbeat (beat 2 of a 2/4 bar). `bar` and `beat` come from the performed quarter position, so a repeat sign closes bar 8 with the next pass's upbeat and every pass is an even number of quarters. The file's own measure numbers stay as `kbar`. "224 bars performed" means numbered barlines passed in plan order, which is what the spec counted; the performed length is 447 quarters, not 448 (P1-SCORES.md, item 2).
*Why:* a note's place in the bar must follow from where it sounds; the printed number would put a pass's upbeat in the wrong bar.

## D-010 (2 Nov 2026) What a card's performance fields mean

`dur` is the notated length in seconds; staccato, arpeggio and trill are flags the renderer interprets. A grace note takes no written time: in performance it sits just before the beat of the note it decorates, a 32nd (1/8 quarter) each, 14 below the velocity of its note. Velocity: p 50, f 96, sfp 114 then p, `<` ramps to the next marking. The Ode melody is stored at written pitch with an `oct` shift for where the arrangement sounds it.
*Why:* the Score witness compares written pitch and exact fractions, so register, articulation and grace placement must not change those fields. *Undo:* change `GRACE_Q` and `VEL` in `score/cardlib.py`; the cards, tracks and receipts rebuild.

## D-011 (2 Nov 2026) Tracks are stored uncompressed

`tracks/*.tracks.json` hold int16 little-endian in base64. The gzip-plus-base64 parts the page decodes with `DecompressionStream` are made from them when the page is built (`score/tracks.py:page_part`).
*Why:* compressed bytes depend on the zlib version that wrote them, which would make the receipt fail on a different machine.

## D-012 (2 Nov 2026) Harmony: labelled for the Turca, authored for the Ode

The Turca's chords are labelled by a transparent rule against a hand-checked key table; the Ode's are written out by hand because the spec says the harmony is ours (`docs/HARMONY.md`). Both are grade L; only the arithmetic on them (Roman numerals, tension, contiguity) is checked by a witness.
*Undo:* edit `KEYS` in `score/turca.py` or `HARM` in `score/ode.py`.

## D-013 (2 Nov 2026) Only the Turca's piano is a recording; every other voice is synthesised

The Turca's written notes are played by a recorded grand (Salamander Grand Piano V3, CC BY 3.0: 17 keys by 8 velocity layers, 212 MB, every file's sha256 in `sources/salamander.manifest.json`). Every other voice in both pieces, and the whole Ode, is a Faust program rendered through DawDreamer.
*Why:* a piano is the one sound an ear holds against a real instrument, and everything else can be shaped in code. A synthesised band keeps the credits to one and makes each render a function of the card and the pinned samples. *Undo:* voice another instrument from recordings by adding it to `audio/rack.py`; `NOTICE.md` names its source and licence first.

## D-014 (2 Nov 2026) The Ode's tune is routed section by section, on the card

The composer line `mel` keeps its written pitch. The card's `routing` table says which voices sound it in each section, how many octaves from where the card puts it and how much louder or softer: the first statement is bass and strings, the second strings and electric piano, the third strings and lead, the fourth strings (and an octave down), brass an octave down and lead, and the coda adds the choir. Check S16 holds every route to declared instruments, whole octaves of at most 3 and velocity offsets of at most 30.
*Why:* the spec lets the tune pass between voices, while the Score witness compares composer notes in written pitch; the voicing lives in a table and the notes stay as notated. *Undo:* edit `ROUTING` in `score/arrange_ode.py`, rebuild the cards and tracks, rewrite `receipts/p1-scores.json` and `receipts/p2-audio.json`.

## D-015 (2 Nov 2026) The masters aim at minus 14.00 LUFS with a true-peak ceiling of minus 1.5 dBTP, held by our own limiter

pyloudnorm sets the loudness; `mix.limit` holds the peak. pedalboard's limiter was tried first and was not transparent (a 0.5 impulse came out at 1.0). The ceiling is minus 1.5 because at minus 1.2 our meter read minus 1.20 and ffmpeg read minus 1.0, exactly on the spec's limit; at minus 1.5 they read minus 1.50 and minus 1.3.
*Why:* streaming services normalise to about minus 14 LUFS, and the limit is minus 1.0 by any meter. *Undo:* the defaults of `mix.master`, then render again (`docs/MIX.md`).

## D-016 (2 Nov 2026) CI judges the audio by thresholds, not by hashes

`receipts/p2-audio.json` records the masters' sha256 and says they hold on the machine class that made them (three fresh renders gave the same bytes). The Faust voices are compiled by LLVM for the host CPU, so another machine may differ in the last bit while sounding the same (S). The CI audio job renders both pieces and runs the Ear witness; it does not compare hashes.
*Why:* a receipt that goes red on a different CPU says nothing about the sound. *Undo:* once a runner's hashes are seen to match, the job can also run `receipts.py check receipts/p2-audio.json`.

## D-017 (2 Nov 2026) The Ear witness reads onsets with a window that fits each sound

Drums are read with a 128-sample window (2.7 ms), the piano with 1,024 (21 ms); the limits are a median of 5 ms and a 95th percentile of 15 ms over at least 20 isolated onsets, with graces, rolled chords and crowded hits left out.
*Why:* measured on synthetic snares at exact sample positions, the piano's window reads a click 10.0 ms early and the drum window 1.0 ms early (C), so one window for both would have broken one of them. The witness is trusted for shifts (a sound moved by 20 ms reads 20 ms later) and not for absolute offset. *Undo:* `IMPULSIVE` and `PIANO` in `witnesses/ear.py`.

## D-018 (2 Nov 2026) The score receipt covers the arrangement code

P1's receipt listed the notated sources. P2 added the arrangement layers (`score/arrange_lib.py`, `arrange_turca.py`, `arrange_ode.py`), which change the card bytes, so they are now inputs of `receipts/p1-scores.json`; the receipt carries a note saying why it was rewritten. The composer notes did not change, and the Score witness shows it (S1: pitch, onset and duration equal the source, 0 missing and 0 extra).
*Why:* a receipt that does not name the code that makes the bytes cannot see drift in that code. *Undo:* none needed.

## D-019 (2 Nov 2026) The page owns the clock; a world has two buses and no Script nodes; every event is a texel

X_ITE has no `browser.currentTime`, so the page decodes the master into a Web Audio buffer, plays from it, reads the heard time from `getOutputTimestamp` and sets `FractionBus.set_fraction` each frame. A ROUTE carries `SecondsBus` to every shader's `u_time`. A thing that can light (a thread's row, a pin, a tooth, a tile, a chord) is a row of an event texture: sorted events of on-time, off-time, three bytes and the card's note index, with times as 24-bit fractions of the scene's length (about 13 microseconds over 216 s). The witnesses use `?clock=manual` so a piece can be walked without waiting for it.
*Why:* the picture follows the audio the page really plays, to the sample; a world with no scripts validates anywhere and runs under the host's policy; a shader needs `u_time` and its table and nothing else. *Undo:* not cheap; the buses and tables are the base of `gen/worldlib.py`.

## D-020 (2 Nov 2026) The page's camera is a second viewpoint, `Free`, not an offset on the directed one

X_ITE 16.5.1's `Viewpoint` has no `positionOffset` or `orientationOffset`. The directed camera (`Cam`) is driven by the shot list. When the viewer grabs, the page copies the pose into `Free`, binds it and drives it; after four idle seconds it eases back and binds `Cam`. The world never binds `Free` itself.
*Why:* the directed track keeps running underneath, so the return lands where the piece is now. *Undo:* none needed.

## D-021 (2 Nov 2026) A tapestry cell belongs to one note of its row, picked by an integer hash the shader and the page share

Row *r* of a statement is woven at `t0 + (r + 0.5) / 384 * (t1 - t0)`. The candidates are the notes of that statement's families sounding then, and the owner is `hash2u(col, row) mod n`, in 32-bit wrap-around arithmetic, the same function in `tapestry_fs.glsl`, `world_ode.py` and `page/hover.js` (eight vectors are written into the map and checked by a unit test and by the hover test). A row with no sounding note stays bare linen. The picture itself is a procedural stand-in (`gen/picture_ode.py`), until the generated picture of P4.
*Why:* a float hash differs between GPUs and an integer one does not, so the page can name the note a thread belongs to without asking the GPU. *Undo:* change the three copies together.

## D-022 (2 Nov 2026) Hover reads the worlds' own TouchSensors, and effect shapes let the pointer through by SAI

Learn mode names the note under the pointer through four TouchSensors (`HoverTap`, `HoverBelt`, `HoverPins`, `HoverTiles`). The page listens to `hitPoint_changed`, turns the hit into a cell, hole, pin or tile and looks it up in the card's tables (`data/<piece>.json`). X_ITE picks on the GPU, so any shape in the way hides a sensor's shape, however faint: the Ode's light shafts hid the whole tapestry (C: with them removed the sensor reported hits on the tapestry plane). `Shape.pointerEvents` lets the pointer through, but it is X3D 4.1 and the worlds are 4.0, so the worlds name their effect shapes (`Fx_Shafts`, `Fx_Halo`, `Fx_Flares`) and list them in the map, and the page sets the field by SAI.
*Why:* the worlds stay valid 4.0 files and nothing in a file depends on the page. *Undo:* write `pointerEvents='false'` on those shapes and declare version 4.1, if the validator and the host take it.

## D-023 (2 Nov 2026) CI judges the worlds by the witnesses, not by their hashes

`receipts/p3-worlds.json` records the sha256 of both worlds, their maps and their reports and says they hold on the machine class that made them (a rebuild gave the same bytes six times here). The generators use numpy and Pillow, which may differ in the last bit on another CPU (S); this machine has numpy 2.5.3 and the pin is 2.5.4. The `page` job prints the worlds' sha256 so a match with a runner can be seen.
*Why:* as D-016, a receipt that goes red on a different CPU says nothing about the worlds. *Undo:* once a runner's hashes match, the job can also run `receipts.py check receipts/p3-worlds.json`.

## D-024 (2 Nov 2026) Some failures are harmless and named; the gate's int-literal warnings stay a count

The Host witness counts as blocked any request the server refused or the browser cut, any policy violation, and any file asked for that is not in the published set, except three named cases: X_ITE cancels the world request after the server has answered 200 (`net::ERR_ABORTED`, classified by the server's own log); X_ITE's interface font is refused by the policy copy; its tangent generator's WebAssembly will not compile under it. The page uses none of the three (the `<x3d-canvas>` attributes `splashScreen`, `contextMenu`, `notifications` and `timings` are set to "false", which is why no font is asked for). The gate's `glsl-int-literal` rule is a scope-blind heuristic (it takes a name such as `n`, `i`, `base` or `m` for a float wherever any function declares it so) and warns 83 times on the Ode and 163 on the Turca; every shader compiles and links in X_ITE, whose GLSL ES 3.00 has no implicit int-to-float conversion, so none is a real error (C for the compile, L for the cause). The counts are kept in `build/runs/gate.json`.
*Why:* a witness that filters nothing is noise and one that filters silently is worse. *Undo:* `harmless` in `witnesses/harness.mjs`; write the literals as floats to silence the rule.

## D-025 (2 Nov 2026) The barrel changes band only in silence, and two silent crossings are allowed and named

The Turca's barrel has one band per section and slides to the next at each section change; a test holds that no note sounds during a slide (12 slides, 60 to 320 ms). A pin meets a tooth with no note under it twice in the whole piece, at 174.583 and 174.643 s: the pickup graces of the second ending, whose pins sit on band I, which the first statement of that section turns past as well. The test allows at most three and names them.
*Why:* a pin that is a written head cannot also be missing from the barrel, and a second set of pins for the graces would break the rule that pins are exactly the written heads. *Undo:* none needed.

## D-026 (2 Nov 2026) The Ode's words are laid by four-bar phrase, as a reading aid

The score card has no words. The page shows the eight lines of Schiller's stanza with an English gloss, on the four-bar phrases of each statement: the first statement lines 1 to 4, the second 5 to 8, the third 1 to 4 then 7 and 8, the fourth 5 to 8 then 1 and 2, the coda 7 and 8. It is not Beethoven's underlay, who repeats and reorders words; the page's credits say so.
*Why:* the page needs a line to show, and claiming a true underlay would be a false claim. *Undo:* `LINES` in `page/build_page.py`.

## D-028 (2 Nov 2026) The hover test teleports its camera and waits for a sensor hit that comes after it aims

The first CI run of the `page` job failed one check, "a lit tile names the lighting note": the card read was the previous look's tile (sector 4, "A · octave 4"), not the E4 tile the test had aimed at. It failed here as well when the same tree was run again. A scratch run (C, `NOBIND` and `TELEPORT` variants of one script, four floor looks each) found the cause: the worlds keep X3D's default `NavigationInfo` transition (one second, LINEAR), X_ITE starts one each time `set_bind = true` is sent, even to a viewpoint that is already bound, and the pointer's pick reads the old pose until it ends. A down-looking floor view draws fast, so a few frames last a few milliseconds and the pick was still at the old pose. A pose set on the bound viewpoint without a bind took effect at once in all four looks, which is how the page's rig works (it binds once per grab and then sets the pose each frame), so the page is right and the test was not. `look()` now sets `transitionType` to TELEPORT on the scene's NavigationInfo, clears the card, notes the page's hit counter (`Loomsong.hover.hits`), moves the pointer and waits for the counter to rise and the card to show, and returns nothing when no hit comes; a card left up from the last look can no longer be read as the new one.
*Why:* a test that reads whatever card is showing passes or fails with frame speed. *Undo:* none needed; the counter is one number on the page.

## D-029 (2 Nov 2026) The page reports how it ran, to its own store, only where the host gives one, and the source never names the host

`page/report.js` collects what the Fps, Sync and Host-policy witnesses cannot learn in the build sandbox: the browser string, the graphics renderer, the screen, whether the host lets the page compile WebAssembly and start a blob worker, how many seconds each world took to arrive, how the clock was set up (`webaudio` means the `.mp4` master decoded, `element` means it did not), frame times while a piece plays (median and 1 % low in frames a second, frames over 33 and 50 ms) and what the host's policy refused. It writes one small document per page load, `reports/<id>`, through the Artifact `db` capability; the artifact's rules let only editors read or write it. Where there is no store (every witness, a plain server) it probes nothing, writes nothing and says nothing. It holds no names, no addresses and no pointer or key data, and the splash says what it sends. Writes go one at a time, on a real change and once a minute while playing.
The host's runtime object is named by the build (`LOOM_HOST_API` when `page/build_page.py` runs, kept in the page's config), never by the source, because D-001 keeps vendor names out of this repository and the leak sweep holds it to that. The witnesses name a stand-in in the address (`?clock=manual&hostapi=NAME`), honoured only with the test clock.
*Why:* the real host's GPU, WebAssembly, blob-worker and AAC behaviour is the largest S left in P3 and cannot be seen from here. *Undo:* leave `report.js` out of `build_page.py`; nothing else depends on it.

## D-027 (2 Nov 2026) The audio-clock probe fits over 8 s, not 2.5 s, with the tolerance unchanged

Probe C5 asks whether the Web Audio context clock advances at 1.000 +/- 0.001 of `performance.now()`. It fits a line to `currentTime` against `performance.now()`, a sample a frame. `currentTime` moves in audio-callback steps (the context reports a 10 ms base latency), so a stall of 3 ms at either end of a 2.5 s window moves the fitted slope by 0.0013, more than the tolerance. The `worlds` job of the first push of P3 read 0.998667 over 2.5 s on a shared runner while C6 (`getOutputTimestamp`, the pairing the page reads each frame) read 1.000000 in the same run (C, job log; the raw rows were not kept, so the cause is L). It had passed in the eight CI runs before it (runs 4 to 11; the first three failed earlier, at the probe worlds). A scratch study on this machine (C, 4 cores; each recording 8 s, the slope fitted on every 2.5 s window and on the whole 8 s): with no load, the 8 s fit was within 0.00012 of 1 in 4 of 4 recordings, and 1 of 1,256 overlapping 2.5 s windows missed the tolerance (worst 0.00127); with the four cores kept busy by other processes, 5 of 6 recordings fitted within 0.00027 over 8 s, one had a starved audio thread and ran at 0.984 (126 of its 302 windows missed), and in another 17 of 317 2.5 s windows missed while its 8 s fit stayed within 0.00027. The window is now 8 s and the tolerance is the same; the rows are kept in `probes.json` so a red C5 can be read afterwards. A starved runner can still fail C5, because then the audio clock really does run slow; that is a re-run, not a fix. The page does not depend on C5: it reads the output timestamp each frame, so no drift accumulates (C6, Sync stays at one frame).
*Why:* a check whose noise equals its tolerance reports the runner, not the clock. *Undo:* pass 2500 to `window.probe.clock` in `witnesses/probes.mjs`.

## D-030 (2 Nov 2026) A generated picture is an upgrade behind a switch; the stand-in is always built and tested too

`art/manifest.json` names each AI-made picture the worlds can use (file, size, sha256 of the file and of the generated source it was made from, the prompt it came from) and gives it a `use`, `ai` or `procedural`. `gen/artlib.py` answers `use(item)` to the generators; a picture whose file is missing, or whose sha256 differs from the manifest, is never used (the item falls back and `status()` says why), and `LOOM_ART` / `LOOM_ART_<ITEM>` override the manifest. Both worlds build both ways (`--out DIR` puts the stand-ins beside the pictures), and CI runs the gate, Behaviour and Eyes on the stand-ins as well as on the worlds with their pictures.
*Why:* the spec's floor rule (every layer above the floor can fail without sinking the build), and a world must never build from a picture nobody can account for. *Undo:* set `use` to `procedural` in the manifest.

## D-031 (2 Nov 2026) The Ode's generated picture is woven by fitting each cell to the nearest of the five threads, in linear light

The tapestry's rule is that every cell is a thread and every thread belongs to a note, so a generated picture cannot be pasted on; it is quantised. `picture_ode.quantize()` reduces the picture to the 256 by 384 cells and, for each cell, picks the thread (indigo, silver, gold, ivory; crimson is kept for the border) whose ink, scaled by a brightness from 0.32 to 1.15, is closest in linear light (projection for the brightness, smallest residual for the thread), and stores the brightness as the cell's tone. The shader paints the thread's ink times that tone times the weft, so the picture shows through the loom. Two crimson border threads (columns 7 and 248) frame it; the stand-in's short crimson foreground threads are left out of the picture (they would cut across it). The result is deterministic and 12 unit tests hold it (each ink finds its own thread, darks stay the darkest indigo, light greys are silver, a changed file is never used).
*Why:* a thread fixes a hue family and the weft sets how bright it reads, so a cell is best explained by a thread and a free brightness together, and the shader mixes light, not sRGB bytes. *Undo:* `LOOM_ART_ODE_TAPESTRY=procedural`.

## D-032 (2 Nov 2026) The dome's twelve motifs are one atlas with mirrored gutters, read through a mirrored lookup

`art/dome-motifs.jpg` is 4 by 3 tiles of 512 px; each picture (480 px) sits in a 16 px frame that is its own mirror image, and `motif()` in `gen/shaders/motif_lib.glsl` reads a tile with `m = 1 - abs(1 - mod(f, 2.0))`, so any coordinate beyond a tile's edge reads its own reflection and never a neighbour's colour, and a picture need not tile to be used. The texture is mipmapped with anisotropy 8, so the tiles stay clean when the dome is seen at a slant. A tile whose texel has alpha other than 1 (the picture has not loaded, or failed) leaves the dome's own procedural tile in place.
*Why:* a flat atlas bleeds across tile borders under any filter; reflected gutters remove the border without a second texture. *Undo:* `LOOM_ART_DOME_MOTIFS=procedural`.

## D-033 (2 Nov 2026) The atlas's rows run from the top, because X_ITE 16.5.1 reads an `ImageTexture` that way

The first dome showed the wrong motifs on the top and bottom rows: X_ITE 16.5.1 puts an `ImageTexture`'s top row at texture coordinate v = 0, the opposite of the X3D text, so the row of tile *t* is `floor(t / 4)` counted from the top. The Atlas witness (`witnesses/atlas_test.mjs`) now photographs a flat page of the twelve motifs drawn through the dome's own lookup and compares every one, on a 7 by 7 grid, with the same motif in the file as it is, flipped, mirrored and turned; the old row order turned it red (mutation-checked) and the fix turned it green.
*Why:* a picture upside down on a dome would never fail a witness that only asks whether pixels are lit. *Undo:* none needed; the witness holds it.

## D-034 (2 Nov 2026) The nearest-filter rule for data textures leaves pictures alone

The Loomsong trap `data-texture-nearest` read every texture a shader samples as data (a note table must be sampled exactly, with no mipmaps). A generated picture is not data. The rule now treats a `PixelTexture` as data always and an `ImageTexture` or `MovieTexture` as a picture when its DEF starts with `Pic_` (it may filter and mipmap); anything else is still data. Tests in `witnesses/test_loomsong_rules.py`.
*Why:* the alternative was to turn the rule off for the atlas, which would also have let a data texture through. *Undo:* rename the atlas away from `Pic_` and the old rule applies.

## D-035 (2 Nov 2026) A picture in the repository holds its pixels and one line of ours; the animated cards stay out

Image metadata is where a vendor's name, a camera, a content-credentials block or a prompt hides. `tools/prep_art.py` rebuilds every generated picture from its raw pixels (a new image, nothing of the original's chunks), sizes it, writes one comment ("AI-made: ...") and records the sha256 of the result and of the source. `witnesses/leak_sweep.py` now reads the structure of every PNG and JPEG (chunks, segments; not a search for words, which compressed pixels would trip by chance) and flags anything except the pixel chunks, a JFIF header and a comment that starts "AI-made" or "Test pattern"; bytes after the end of the image are flagged too. The animated cards are video, 3 to 6 MB each after the web encode (the generated originals are 27 to 36 MB), and stay out of the repository: the history of a repository keeps every version of a binary file for good, and a card can be made again from its prompt and its source with `tools/prep_cards.py`. The repository holds that tool, the prompts and their sha256 (`docs/PROMPTS.md`), and a build without the cards is a page without cards.
*Why:* a public repository cannot take back a file. *Undo:* commit the cards (each under the 5 MB limit) and add a video rule to the sweep first.

## D-036 (2 Nov 2026) A card is a layer, never part of the timing

`page/cards.js` shows three animated pictures: one behind the title card and Play (it loops, muted), one behind the end card (the hall between the pieces), and each piece's opening, which plays once over the world as the music starts, carries the piece's name and dissolves into the world on the page's own timer (the video may stall, the page cannot). The music starts at the press, never after a card; Escape, Enter or the Skip chip ends an opening early; Calm and reduced motion leave the opening out and hold the looping cards on their posters. A card is used only if the build shipped its video and its poster and they match the sha256 in the media manifest; with none, the page is as it was. Under the test clock cards are off unless the address says `cards=on`, so a witness is never looking at a covered world. Every card says what it is on the card, in the corner and in the credits; CI builds four two-second test patterns (`tools/prep_cards.py --synthetic`) that exercise all of this and say "Test pattern", never "AI-made" (`witnesses/cards_test.mjs`, 23 checks).
*Why:* the generated media builds the stage and never the music's timing (spec); a card that waited for a download would make the music late. *Undo:* leave `cards.js` out of `build_page.py`.

## D-037 (2 Nov 2026) A hover card shows the score card's own bar and beat

`LoomUI.noteInfo` worked bar and beat out again from the note's seconds, which the page's table keeps to four decimals. The Ode's choir has a note on a bar line (280 quarters, `ode.S41.choir.A.0027`), and the helper that gives the hover test its expectation worked it out from the card's six-decimal seconds, 279.9999996 quarters, and said bar 70 beat 5 where the page said bar 71 beat 1. The fault was in the test's arithmetic (the card's own record says bar 71, beat 1), and a different picture only chose different cells to look at. Both now read the card's record (columns 5 and 6 of a note's row; `hover_expect.py` reads the same fields); the transport's bar and beat are still worked out from the clock and held to the card by the page test's 60 notes a piece.
*Why:* a hover card is a statement about a note, and the card is the authority on its notes. *Undo:* none needed.

## D-038 (2 Nov 2026) The photoreal splat world waits for the GPU; the dust splats stand in meanwhile

The three backdrop clips pass the Pose witness on a CPU (COLMAP, all 48 sampled frames registered each, median point error 0.38 to 0.46 px). Training the photoreal splat world and the Fidelity witness (PSNR at least 22 dB, SSIM at least 0.75 on held-out frames) need the GPU virtual machine, which is stopped and which a session may not start without the owner's typed yes. A CPU "dust" world (the sparse points, as small splats) shows the camera path and the room's shape in X_ITE, graded for what it is, a stand-in. Nothing in a world uses either yet.
*Why:* starting the machine spends money and is the owner's call; the floor needs neither. *Undo:* none; the job script and its training input are ready (`loomsong/p4/`, private).

## D-039 (2 Nov 2026) The worlds' receipt is rewritten for P4, and the P3 receipt is kept as the record of its run

P4 changed what the world generators read (`gen/artlib.py`, `art/`, `gen/shaders/motif_lib.glsl`) and the generators and the dome's shader themselves, so `receipts/p3-worlds.json` can no longer be checked: its inputs changed on purpose and a check reports STALE. `receipts/p4-worlds.json` lists all 49 inputs and the seven outputs (both worlds, their maps and reports, and the dome's atlas copied beside the Turca) and a rebuild gives the same sha256 here (the Ode `b43ad7c0...`, the Turca `64f6f459...`). The P3 receipt stays as the record of that run, with a note saying so; it is not checked by CI.
*Why:* as D-018, a receipt has to name the code that makes the bytes, and an old record is not rewritten to say something new. *Undo:* none needed.
