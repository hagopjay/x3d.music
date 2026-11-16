# Lineage: where each number in a world comes from

The method behind this note is Umair Ali Khan's article "How I Added Traceability in Structured Data Extraction with AI": a value is
kept with the exact evidence it was read from, and plain code, with no model, checks that the evidence holds the value and says where it
sits. This repo already does that, in a stronger form, because the card is the single source of truth and nothing reads the audio to find
timing (`README.md`, rule 1). This note records what exists, the one gap, and a small addition that closes it: a time-span selector,
`score/tspan.py`, with its witness, `witnesses/test_tspan.py`.

Read at `5d9adfc`. Grades: Confirmed = read in the code or run; Likely = follows from Confirmed facts.

## What exists (Confirmed)

1. **Source to card, note by note.** Every composer note has an `id` and a `src` pointer (`docs/SCORE-SCHEMA.md`): `line:column` of the
   Humdrum file for the Turca, `m<measure>.<pos>` in the MusicXML for the Ode. The Score witness re-reads the source with another parser
   and checks each pointer (`witnesses/score_check.py`, S3a and S3b), and checks the source file's sha-256 (S0). That is the article's
   find-and-compare with a pointer in place of a quote.
2. **Arrangement notes say so.** `src: "arr:<rule>"` (`score/arrange_lib.py`, checked by S11). Counted from the cards: the Ode has 3,101
   notes, 327 from the composer (63 distinct pointers) and 2,774 from 33 rules; the Turca has 6,555 notes, 2,810 from the composer (1,613
   distinct pointers) and 3,745 from 20 rules. Share of notes that carry a source pointer: Ode 10.5%, Turca 42.9%. The rest are derived by
   a named rule, which is the article's `unchecked` with a reason attached.
3. **File chain.** `receipts/*.json` (`loomsong.receipt/1`) records the command, `SOURCE_DATE_EPOCH` and the sha-256 and size of every
   input and output, and `check` reruns the command. Worlds are bit-identical only on the machine class that made them (D-023), so CI
   judges worlds by witnesses, not hashes.
4. **Hover.** `page/hover.js` maps what the pointer rests on, through the world's TouchSensors and `build/worlds/<piece>.map.json`, to a
   note index; the card then names pitch, instrument, bar, beat, composer or arrangement, and `id`. `witnesses/hover_expect.py` recomputes
   the expected line from the card (D-037).
5. **The note id reaches the GPU.** Event textures carry the card's note index (`gen/worldlib.py`, `EventTable`).

## The gap (Confirmed)

Inside a generated world there is no record of what a driver is. Both worlds have zero `<Metadata>` nodes and four head metas (title,
description, generator, created). The path card, feature (Python), bus keys (X3D), ROUTE, shader uniform, pixel can be followed only by
reading `gen/world_ode.py` and the GLSL. For example `ActBus` (`activity_keys`), `TensionBus` and `LayerBus` appear in no document under
`docs/`. A reader of the X3D file cannot tell that `ActBus` is "velocity-weighted onsets near each second, smoothed three taps" over a
window of a named card.

No value in any world comes from audio today: `tracks/README.md` says the Texture channels arrive in P2, and the shipped tracks files
hold none. So the article's limit, "a quote is not mapped to a time in the recording", has no live case yet. It will on the day a Texture
channel lands.

## The time-span selector, `tspan/1`

```
{"kind": "tspan/1", "clock": "performance",
 "t0": 57.0, "t1": 58.0,                 seconds on the performance clock, half-open [t0, t1), six decimals like the card
 "q0": "104", "q1": "105",              the same window in exact quarters; bar0/beat0/bar1/beat1 on the performed grid
 "fs": 60, "k0": 3420, "k1": 3480,      frames of the 60 Hz tracks: k0 <= k < k1  <=>  t0 <= k/60 < t1
 "onsets": ["ode.S2.mel.M.0031", ...],  ids of the notes whose onset lies in the window (grace notes excluded): the evidence
 "audio": {"sr": 48000, "s0": ..., "s1": ..., "sha256": "..."}   optional, for a rendered master pinned by hash }
```

`check(selector, clock)` re-derives every field from the card (quarters and seconds through the repo's own `TempoMap`, bar and beat
through `cardlib.metric`, frames, the onset set, the sample range) and returns what differs. `bus_times` and `keys_in_window` map a window
to the keys of an interpolator in a generated world (key fraction times D is seconds). Verdicts map onto the article's four: `verified` when every field
re-derives and a value recomputed from the evidence alone equals the scene's; `check` when something differs; `unchecked` when there is
no evidence list (a rule-made note, or a texture value whose master is absent); `reworded` when the value is reproduced only after a
documented transform.

### Results (Confirmed; run in a clone at `5d9adfc`, Python 3.13)

* `witnesses/test_tspan.py`: 14 tests. With no generated worlds 11 pass and 3 skip; with the Ode generated
  (`SOURCE_DATE_EPOCH=1793491200 python3 -I gen/world_ode.py`) all 14 pass.
* Every one of the 3,101 Ode and 6,555 Turca note starts round-trips quarter to time to bar and beat equal to the card's own time (at most 1.5e-6 s).
* Ten damaged selectors (one field moved at a time) each go red.
* `BeltPos` key `b` equals the time of quarter `b` on the tempo map for all 385 beats of the Ode, which has a 33-entry tempo map with a
  ritardando (largest difference under 2e-5 s).
* All 217 `ActBus` keys are recomputed from the selector's onset ids alone and equal the file's `keyValue` within 5.1e-4 (the file rounds to three places).
* A 14-mutant spot check of the module, run on copies in scratch, was killed after two tests were added (the first run left three alive).

Two findings from making that test honest:

1. The lineage window of a smoothed key is `[t(i-1) - 0.5, t(i+1) + 0.5)`, not plus or minus half a second. With plus or minus 0.5 s,
   200 of 217 keys fail; with the window slid by one second, 201 fail.
2. Key times read back from the file carry up to about 11 microseconds of rounding (seven places of a fraction of D). Without snapping
   them to the millisecond grid the bus was built on, 6 of 217 keys fail (keys 52, 53, 54, 67, 68, 69), all because bass onsets sit
   exactly on a window edge. `bus_times(snap=0.001)` fixes it and `keys_in_window` takes `eps = 2e-5`. A selector read back from a
   scene needs that declared tolerance; one computed from the card needs none.

### What it does not do

* Nothing here checks a value that comes from audio: none exists yet. The audio branch (a window to samples, an RMS in dBFS) was run only on a
  synthetic 48 kHz WAV; the real masters are FLAC and need an audio reader that the sweep job does not install.
* The selector is not written into a world yet. See the proposals.
* The three world-dependent tests skip in the `sweep` job, which has no generated worlds. No job runs them; adding the file to the `page`
  job after the worlds are generated would.

## Proposals, not built

| id | what | size |
|---|---|---|
| L1 | A sidecar per piece listing each bus: feature, formula, window rule, source card sha-256, and one `tspan/1` per key (or a rule that yields them); a unit test that the sidecar and the generator agree | M |
| L2 | An `x3dprov` `generate` step in the world's head: `add_step(xml, {op: "generate", tool: "gen/world_ode.py", inputs: [card sha-256, MusicXML sha-256]})` through the `document(extra_meta=...)` hook. In a scratch run on the 3.1 MB Ode world, `add_step` took 0.10 s, `verify()` said `verified`, and editing one `ActBus` key made it `stale`. The caveat is D-023: a rebuild on another CPU gives a new step, not a failed one | S |
| L3 | A coverage line for the card: composer pointers over all notes (Ode 10.5%, Turca 42.9%) printed by the Score witness, so a new arrangement rule moves a visible number | S |
| L4 | A contract for the Texture channels: each audio-derived value carries a `tspan/1` with the master's sha-256, and a world refuses a channel without one | S |

## Credit

Method: the article above and the GAIK toolkit (MIT). `score/tspan.py` is original code for this repo; it copies nothing from either.
