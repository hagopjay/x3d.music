# Mix and master (P2)

How the two masters are made from the score cards, and why the numbers in `audio/recipes.py` are what they are. Everything here is arithmetic on arrays and pedalboard's built-in effects, so a rerun on one machine gives the same samples (C: three fresh renders of each piece, same sha256 every time; `receipts/p2-audio.json`).

Grades: **C** a command or test showed it, **L** reasoned or read, **S** not checked.

## The signal path

```
score card ──► routing ──► stems ──► per-stem chain ──► fader ──► ducking, pan ──► sends ──► buses ──► rides ──► master ──► limiter
```

1. **Notes.** `rack.instrument_notes` hands every instrument its notes. The arrangement layer is played as written. Composer notes go through the card's `routing`: for each composer instrument and section, a list of `{inst, rel, vel, dur}` (octave shift, velocity offset, length factor). The Turca has no routing (its piano plays the written notes); the Ode's tune, one `mel` line, is voiced by different instruments in each section (`score/arrange_ode.py`). Tested in `audio/test_audio.py` (Routing).
2. **Stems.** The grand piano comes from `audio/sampler.py`: the Salamander Grand (Alexander Holm, CC BY 3.0), 17 keys by 8 velocity layers, nearest key shifted by at most one semitone, the two layers either side of a velocity blended, a damper release when the key goes up. The other 19 voices are Faust programs (`audio/faust/*.dsp`) played through DawDreamer at 48 kHz, 32-bit float. A note starts on the exact sample of its written time (C: `FaustVoices.test_a_note_starts_on_the_exact_sample`).
3. **Per stem.** Brought to a common level (minus 23 dBFS RMS over its playing blocks, so every chain's dynamics see the same level whatever the synth put out), then through its pedalboard chain (EQ, drive, compression, chorus), then set to the recipe's `level` in LUFS, then its peaks held to `crest` dB over that level (hats and cymbals arrive 30 dB over their loudness), then trimmed by `gain`. Every chain passes a click without delaying it by more than 1 ms (C: `Recipes.test_every_chain_passes_a_click_without_delaying_it`).
4. **Ducking and pan.** Stems that say so dip at every kick (depth per recipe, time constant 0.12 s); the dips of kicks that overlap take the deeper one and do not add. Balance pan turns down only the far channel.
5. **Sends.** Four shared spaces: hall, room, plate and a dotted-eighth delay (32 percent feedback). Each stem's send is summed before its space and the space runs once. The plate is gated: it opens on every snare, clap and rim hit, holds 0.17 s and closes in 45 ms. Hall and room get 20 ms of predelay, the plate 12 ms. Each return is trimmed so that 0 dB means "returns as much level as was sent" (`SPACE_TRIM_DB`, measured on noise by `mix.calibrate_spaces()`; a test re-measures it).
6. **Buses.** The kit is glued by a 2:1 compressor and a low shelf; the music sum is untouched.
7. **Fader rides (the arc).** Each pass of the form is brought to the loudness its recipe asks of it (LUFS of that pass, relative to the others), passes shorter than 2 s keep the ride before them, and the steps are smoothed over 0.5 s. This is where the build from the quiet opening to the coda comes from, and it is what puts the loudness range inside 4 to 12 LU. The rides the first masters needed are in each `report.json` (`rides_db`; between minus 2.7 and plus 2.3 dB).
8. **Master.** Two 28 Hz high-passes, a gentle low shelf, minus 0.8 dB at 300 Hz, a high shelf at 7.5 kHz, a 1.4:1 compressor; then gain and the limiter, iterated until the integrated loudness is minus 14.00 LUFS with the true peak at the ceiling.

## The limiter

`mix.limit` is our own offline true-peak limiter. pedalboard's `Limiter` was not transparent (a 0.5 impulse came out at 1.0; C, probe), so it is not used.

The true peak of each sample (4x oversampled, as the meter reads it, but measured only where the signal comes within 6 dB of the ceiling) sets the gain it needs. A sliding minimum over plus and minus 2 ms followed by two box filters of the same support turns the gain down before a peak and never after it, and a release of 70 ms brings it back. No latency, no overshoot (C: `Limiter` tests; an impulse comes out at its own sample, the gain is already down 50 samples before it and recovered long after it).

**The ceiling is minus 1.5 dBTP.** The spec wants at most minus 1.0. With the ceiling at minus 1.2 our own 4x meter read minus 1.20 and ffmpeg's ebur128 read minus 1.0, on the line. At minus 1.5 ours reads minus 1.50 and ffmpeg minus 1.3 (C, both masters).

## Levels, and how they were chosen

By the numbers, not by ear: no ear was available to the build. Each stem's `level` was moved until three things held at once: the long-term balance below, a loudness range of 4 to 12 LU, and a stereo correlation of at least 0.2. They are starting values for a listener to move (S).

| Band (re the loudest) | Turca | Ode |
|---|---|---|
| sub 20 to 60 Hz | −11.3 | −12.7 |
| bass 60 to 250 Hz | 0.0 | 0.0 |
| low-mid 250 to 500 | −3.1 | −2.7 |
| mid 500 to 2k | −2.3 | −2.5 |
| upper-mid 2k to 6k | −12.4 | −11.3 |
| presence 6k to 10k | −17.9 | −19.5 |
| air 10k to 20k | −19.2 | −20.7 |

The master is bass-heavy and dark on purpose: a 1982 pop master has its weight under 250 Hz and little above 6 kHz, and the sub band must sit at least 6 dB under the bass band (the Ear witness checks it, E9).

Stem levels in the mix, LUFS at the fader and the stem's peak in dBFS (`report.json`, `stems_in_mix`):

| Turca | level | peak | Ode | level | peak |
|---|---|---|---|---|---|
| kick | −20 | −5.0 | kick | −20 | −5.0 |
| snare | −21 | −5.0 | snare | −21 | −5.0 |
| bass | −21 | −10.0 | bass | −21 | −10.0 |
| davul | −23 | −8.2 | strings | −22 | −7.0 |
| tom | −25 | −10.0 | lead | −22 | −11.2 |
| clap | −26 | −10.0 | brass | −24 | −11.0 |
| pad | −28 | −15.1 | ep | −24 | −14.3 |
| hat | −31 | −17.0 | timp | −24 | −13.1 |
| cymbal | −31 | −16.0 | clap | −26 | −10.0 |
| triangle | −31 | −23.9 | choir | −27 | −15.8 |
| jingle | −35 | −20.0 | rim | −27 | −13.0 |
| brass | −24 | −10.9 | clatter | −29 | −15.0 |
| pno | −18 | −4.3 | pad | −29 | −16.0 |
| | | | tom | −25 | −14.2 |
| | | | cymbal | −30 | −15.0 |
| | | | hat | −31 | −17.0 |

## Rebuild and re-check

```
pip install -r requirements-audio.txt              # pins: DawDreamer 0.9.0, pedalboard 0.9.26, pyloudnorm 0.2.0, soundfile 0.14.0, soxr 1.1.0, scipy 1.18.1; ffmpeg on the path
python3 -I tools/fetch_salamander.py                # about 212 MB into a cache outside the repository; each file is checked against sources/salamander.manifest.json
python3 -I audio/render.py all                      # stems, mix, master, report.json under build/audio/ (both pieces in about 4.5 minutes on 4 cores)
python3 -I witnesses/ear.py --piece all             # the Ear witness: 20 checks, two loudness tools, timing against the card
python3 -I audio/test_audio.py                      # 43 tests, about 12 seconds
python3 -I audio/mutants.py                         # 11 deliberate breakages, each must turn a test red, about 25 seconds
```

`LOOMSONG_CACHE` moves the sample cache. `audio/render.py` caches each instrument's stem by what it depends on (the card, `rack.py`, the shared Faust library, that instrument's own file; the sampler for the piano), so retuning one voice renders one voice and a change of recipe renders nothing.

## Why hashes are not the audio standard in CI

The masters are bit-identical on the machine that made them (C: three fresh renders). The Faust voices are compiled by LLVM for the host's CPU, so another machine may differ in the last bit while sounding the same (S). The audio receipt (`receipts/p2-audio.json`) records the hashes and says so; CI judges the audio with the Ear witness's thresholds, which do not depend on the last bit.
