# x3d.music: Loomsong

Two programmable machines play two pieces of music.

- **World 1, *Ode to Joy*** (Beethoven, 1824): a Jacquard loom in a cathedral of light weaves a tapestry. Each statement of the theme lays down one colour layer, so the picture can only appear when every voice has joined.
- **World 2, *Rondo alla Turca*** (Mozart, 1783): a pinned brass barrel carries every written note as a pin. A steel comb plucks them, a clockwork Janissary band strikes on the beat, and the tiled courtyard floor lights note by note.

Every thread, pin, tile and light is a real note from the score. Nothing is drawn that is not in the score, and no note in the score goes undrawn.

## Proof of concept 2: *Moonlight // Two Ways*

Beethoven's Op. 27 No. 2, from the Adagio into the Presto agitato, is produced in LMMS and shown in X3D. The LMMS project file is XML, and one XSLT stylesheet turns it into the scene, so every box is a note in the project. It is published with GitHub Pages at `/moonlight/`. See `moonlight/README.md`.

## One generator, three outputs

```
score card (JSON)  ──►  the master      audio rendered from the card, in code
   one per piece   ──►  the live page   X3D worlds in X_ITE, the page owns the clock
                   ──►  the film        the same camera track, rendered from the same card
```

The score card is the single source of truth. The audio renderer, the X3D generator, the film scripts and every witness read it; nothing reads the audio to find timing.

## Rules that never bend

1. **Score-true.** No visual event without a score event. Audio analysis may add texture (loudness, brightness), never timing.
2. **X3D is the master** and must validate. Blender owns the film's look.
3. **Every claim is graded** C (a tool ran and showed it), L (read or reasoned) or S (suspected, all model output) and names its witness.
4. **Everything AI-made is labelled** where it appears: images, video, voices.
5. **Never overwrite a demo.** Versions are `v1`, `v2`, and so on.
6. **Generator, not file.** Fix the generator or the card, then build again. Same inputs and seed give the same bytes.

## Witnesses

A red witness stops the build. It is fixed, never explained away.

| Witness | Passes when |
|---|---|
| Grammar, Meaning | the pinned x3d_mcp validator finds 0 XSD errors and 0 semantic errors |
| Traps | `loom_gate.py` and the Loomsong rules find 0 hits |
| Score | composer notes match the source edition exactly, and every drawn event has a score id |
| Receipts | a rebuild from the recorded inputs gives the same sha256 |
| Ear | loudness, true peak, range, stereo correlation and onset error are inside the targets |
| Behaviour, Host, Eyes | the page loads in X_ITE 16.5.1 under a copy of the host's security policy, with a clean console and no black frames |
| Sync, Flash, Fps | picture and sound agree within one frame, no harmful flashes, 60 fps on a real GPU |
| Truth | licences present, AI-made labels present, leak sweep clean |

## Layout

```
sources/    the kern file, the hand-encoded Ode theme, sample manifests (no big binaries)
score/      build_score.py  ->  ode.score.json, turca.score.json (schema in docs/SCORE-SCHEMA.md)
audio/      the Faust voices, the piano sampler, render, mix and master scripts, unit tests and a mutation spot-check (audio/README.md)
tracks/     feature tracks sampled at 60 Hz
gen/        world generators, X3D writer helpers, shaders, the art switch (artlib.py)
art/        the generated pictures the worlds use (the Ode's tapestry picture, the Turca's dome atlas) and manifest.json; AI-made, labelled where they appear
page/       the page: clock, SAI driver, interface, hover, report; build_page.py lays out build/page
blender/    film scripts
witnesses/  the checks above
receipts/   one Loom Receipt per artifact
runs/       per-run witness results
docs/       FACTS.md, DECISIONS.md, PROMPTS.md, PROBES.md (and p0/, the raw probe record), P1-SCORES.md, SCORE-SCHEMA.md, HARMONY.md, MIX.md, P2-AUDIO.md, P3-WORLDS.md, P4-MEDIA.md
moonlight/  proof of concept 2: event lists, the LMMS project generator, the XSLT, the page, its witnesses and the v1 master
tools/      pins.json (every checker pinned), fetch_xite.py, prep_art.py and prep_cards.py (generated pictures and clips into art/ and the page's cards)
build/      outputs (git-ignored)
```

## Status

| Phase | What | State |
|---|---|---|
| P0 | Set-up and probes | done; the probe report is `docs/PROBES.md` |
| P1 | Score cards | built; the Score witness checks both against their sources (`docs/P1-SCORES.md`) |
| P2 | The two masters | built: both at minus 14.00 LUFS, Score 51 of 51 and Ear 20 of 20; no human has listened yet (`docs/P2-AUDIO.md`, `docs/MIX.md`) |
| P3 | The worlds, live | built: both worlds, the page and Learn-mode hover; the gate, Behaviour, Eyes (the program's part), the page, hover and report tests and the Host witness (110 steps a piece) are green; one real machine (an integrated GPU, Chrome on Windows) ran both pieces at about 60 frames a second and allowed WebAssembly and blob workers, as the private preview's own report says; no one has reported how it sounds or looks (`docs/P3-WORLDS.md`, `docs/PROBES.md` I) |
| P4 | Generated media | built in part: the Ode's tapestry is woven from a generated picture, the Turca's dome is tiled with twelve generated motifs, and four animated cards frame the pieces, each labelled AI-made and each prompt in `docs/PROMPTS.md`; every world still builds and passes without them. The three backdrops pass the Pose witness but are not in a world yet (photoreal splats wait for the GPU machine); nobody has looked at it on a real screen (`docs/P4-MEDIA.md`) |
| P5 | Improvement rounds | not started |
| P6 | The films | not started |
| P7 | Publish | not started for Loomsong; the Pages workflow (`.github/workflows/pages.yml`) already publishes proof of concept 2 |

## Licences

Code is MIT (see `LICENSE`). The *Alla Turca* score is a Humdrum encoding licensed CC BY-NC-SA 4.0, so everything derived from it carries that licence. `NOTICE.md` says which folder carries which licence and credits every source.
