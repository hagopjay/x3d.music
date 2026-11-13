# x3d.music, proof of concept 2: Moonlight // Two Ways

Beethoven, Piano Sonata No. 14 in C♯ minor, Op. 27 No. 2 (1801), produced in LMMS and shown as an X3D piano roll.
The LMMS project file is XML, and an XSLT stylesheet turns it straight into the X3D scene.

| Section | Score | Tempo |
|---|---|---|
| Act I | I. Adagio sostenuto, bars 1 to 9 | quarter = 56 |
| Bridge | timpani roll on G♯ (V), choir from E major (III) to G♯ major | 138 rising to 168 |
| Act II | III. Presto agitato, bars 1 to 64 | quarter = 168 |
| Coda | III. Presto agitato, bars 191 to 201 | 168, easing to 150 on the last chords |

The whole project runs at one tempo of 168 BPM. The Adagio is written at three times its note values, so Adagio quarter = 56 exactly. That is a 3:1 metric modulation: the Adagio's triplet pulse becomes the Presto's beat.

## One generator, three outputs

```
kern (pinned, sha256)  ─►  score/*.events.json  ─►  lmms/build_project.py  ─►  LMMS project (.mmp, format 31)
                                                                               ├─►  lmms render  ─►  media/*.v1.mp3
                                                                               └─►  viz/mmp2x3d.xsl  ─►  X3D 4.0 scene
```

The project is the single source of truth. The page reads the project's own tempo-automation clip to place the playhead, and nothing reads the audio to find timing. The page runs the stylesheet live with `XSLTProcessor` where the browser still has one. Elsewhere (Chrome 158 and later) it loads the scene that libxslt made from the same stylesheet at build time.

## Build

```bash
python3 -I tools/fetch_xite.py                        # pinned X_ITE, as the page's own files
python3 -I moonlight/page/build_page.py               # build/pages: landing + /moonlight/, receipt checked
python3 -I -m pytest -q moonlight/witnesses
node moonlight/witnesses/page_smoke.mjs               # after npm ci and npx playwright install chromium
python3 -m http.server -d build/pages                 # then open http://localhost:8000/moonlight/
```

Re-rendering the master needs LMMS 1.3 alpha or later (1.2.x cannot read format 31) and `FluidR3_GM.sf2` at `/usr/share/sounds/sf2/` (Debian/Ubuntu: `apt install fluid-soundfont-gm`):

```bash
lmms render build/pages/moonlight/data/moonlight-two-ways.v1.mmp -f flac -o master.flac
```

`lmms/levels.py` and `lmms/meter.py` are the stem meter and clip check used for the mix. `lmms rendertracks` writes the stems, and `NO_MASTER=1` builds the project without the master chain.

## Witnesses

| Witness | Passes when | Grade |
|---|---|---|
| Score | every event in the three event lists is a piano note at the right tick and key, and re-extracting the pinned kern files gives the committed lists | C |
| Project | format 31, 4,932 notes in range, every automation clip points at a real model, every track routes to a real mixer channel, the master limiter detects peaks | C |
| Scene | one box per note, one lane per instrument track, one shared Box, and the nodes the page drives are present | C |
| Clock | the tempo map from the project puts the Presto downbeat at 42.17 s ± 0.05 s, the onset measured in the v1 master | C |
| Receipt | rebuilding the project and the scene gives the sha256 in `receipt.v1.json`, and the master's bytes match | C |
| Page smoke | the built site loads in headless Chrome (software GL), all 4,932 boxes are in the running scene, playing moves the playhead and the follow rig, 60 s is in the Presto, a still is neither black nor blown out, there are no page errors or missing files, and the page loads again with XSLT removed | C |
| Ear | the v1 master has 0 clipped samples and a −1.15 dBFS peak in the FLAC (the 192 kb/s MP3 decodes to −0.58 dBFS); about −13 dBFS RMS in the Presto | C for the numbers; no human has listened yet: S |
| Looks | a real GPU and a real screen | S: only software GL has run it |

The rebuilt v1 project is byte-for-byte the project LMMS rendered the master from (C).

## What is AI-made

The arrangement, the instrument layers, the mix and the stylesheet were generated, and the page says so in its corner note. Beethoven's notes are not changed: the full piano part is played as written, and every other layer is derived from it by rule (`build_project.py` says which rule makes which layer).

## Rules kept

- Versions are `v1`. A later mix is `v2`, and v1 stays.
- The master is under 5 MB (3.7 MB, 192 kb/s).
- The kern files are not committed; they are fetched at a pinned commit with their sha256.
- X_ITE comes from `tools/fetch_xite.py` at the repository's pin, never from a CDN.
