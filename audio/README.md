# audio/

The Loomsong audio, made in code from the score cards (`score/*.score.json`). Signal path, levels and the reasons for them: `docs/MIX.md`. What was built, measured and still unknown: `docs/P2-AUDIO.md`.

| File | What it does |
|---|---|
| `rack.py` | Hands each instrument its notes (composer notes through the card's routing, arrangement notes as written) and renders the Faust voices through DawDreamer at 48 kHz |
| `faust/*.dsp`, `faust/common.lib` | The 19 synthesised voices and the library they share |
| `sampler.py` | The grand piano: Salamander Grand (CC BY 3.0, `NOTICE.md`), 17 keys by 8 velocity layers, fetched by `tools/fetch_salamander.py` |
| `recipes.py` | Each stem's chain, level, ducking, pan and sends; the master chain; the arc of rides for each piece |
| `mix.py` | Stem normalising, ducking, sends and spaces, buses, rides, the master and its own true-peak limiter |
| `meter.py` | Loudness (pyloudnorm), true peak (4x oversampled), range, band levels, stereo correlation |
| `render.py` | One command: stems, mix, master and `report.json` per piece, under `build/audio/` |
| `test_audio.py` | 43 unit tests: meters, curves, rides, limiter, sampler rules, routing, every voice and chain |
| `mutants.py` | Breaks the code on purpose, one expression at a time, and checks that a test notices (11 of 11) |

```
pip install -r requirements-audio.txt        # and ffmpeg on the path
python3 -I tools/fetch_salamander.py         # about 212 MB into $LOOMSONG_CACHE (default ~/.cache/loomsong), every file checked against its sha256
python3 -I audio/render.py all               # both pieces in about 4.5 minutes on 4 cores; stems are about 1 GB a piece and are not committed
python3 -I witnesses/ear.py --piece all      # the Ear witness
python3 -I audio/test_audio.py && python3 -I audio/mutants.py
```

The masters are not committed. The AAC `.mp4` the listening page plays is encoded from the WAV by script.
