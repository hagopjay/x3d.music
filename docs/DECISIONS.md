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

