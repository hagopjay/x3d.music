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
