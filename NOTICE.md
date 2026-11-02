# Notice: licences and credits

Which folder carries which licence, and who must be credited. The leak sweep and the Truth witness read this file; a source missing here fails the build.

## By folder

| Path | Licence | Why |
|---|---|---|
| Code: `witnesses/`, `gen/`, `page/`, `audio/` (scripts), `tools/`, `blender/`, `tracks/` (scripts), `.github/` | MIT (`LICENSE`) | Our own code |
| `sources/sonata11-3.krn` | CC BY-NC-SA 4.0 | Unmodified copy of the Humdrum encoding credited below |
| `score/turca.score.json`, `tracks/turca.*`, and every audio, frame and film derived from the *Alla Turca* score card | CC BY-NC-SA 4.0 | Adapted from the encoding credited below; share-alike applies to adaptations |
| `sources/ode-theme.musicxml`, `score/ode.score.json`, `tracks/ode.*` | MIT for the encoding; the melody is public domain | The theme is Beethoven's (1824), encoded by hand from the public-domain tradition |
| `docs/` | MIT | Our own text |

Commercial use of anything derived from the *Alla Turca* score card needs a fresh hand encoding of the 1878 edition (public domain) that does not use the file credited below. That is listed as longer-term work, not done.

## Credits

**Mozart, Piano Sonata in A major, K. 331 (300i), third movement, *Alla Turca*** (1783). The composition and the Alte Mozart-Ausgabe (Breitkopf & Härtel, 1878) are in the public domain. The digital encoding used here is:

> Digital edition of Mozart piano sonatas, from volume 20 of the Alte Mozart-Ausgabe (1878).
> Copyright (C) 2004-2018 Craig Stuart Sapp. https://github.com/craigsapp/mozart-piano-sonatas
> File `kern/sonata11-3.krn`, commit `0f1f49d`, licensed CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0).

Changes made: the file is parsed to note events with exact rational onsets and durations, repeats are expanded following the file's own repeat plan, and an arrangement layer (drums, bass, pads, brass, percussion) is added around the written notes. The written notes themselves are not altered.

**Beethoven, Symphony No. 9 in D minor, Op. 125, finale** (first performed 1824). Public domain. Text of *An die Freude* by Friedrich Schiller (1785), public domain.

## Samples and tools

Listed as they are added. A sample library is named here with its licence and the commit or hash it was taken at before any audio made from it is published.

| Item | Use | Licence |
|---|---|---|
| X_ITE 16.5.1 | The X3D browser, shipped as the page's own files | MIT |
| music21, pedalboard, pyloudnorm, DawDreamer (with Faust), soundfile, mido, librosa | Score parsing, effects, loudness, synthesis, I/O | see each project |
| x3d_mcp validator (fork) | Grammar and Meaning witnesses | Web3D Consortium Open-Source License |
| `loom_gate.py`, `loom_receipt.py` | Traps and Receipts witnesses | as published by their repository |
| Playwright 1.63.0, Chrome for Testing 153 | Behaviour, Host, Eyes, Sync and Fps witnesses and the P0 probes; test tools, not shipped | Apache-2.0 (Playwright); the browser's own notices |
| ffmpeg 6.1.1 | Encodes the audio probe files now and the AAC masters later; an external tool, not shipped | per its build (LGPL or GPL) |
| pytest, numpy, lxml, jsonschema, xmlschema, rdflib, x3d | Witnesses and generators; not shipped | MIT or BSD, see each project |

## AI-made material

Pictures, video and voices made with generative tools are labelled AI-made wherever they appear: the title card, the end credits and the caption of every shared still. Prompts and their sha256 hashes are in `docs/PROMPTS.md`.
