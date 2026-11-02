# Score card schema `loomsong.score/1`

One file per piece, `score/<piece>.score.json`, is the single source of truth: the audio renderer, the X3D generator, the Blender film and every witness read it, and nothing reads audio to find timing. The layout is one top-level key per block and one note per line, so a change shows up as a few lines in a diff.

**Time.** Everything musical is an exact fraction of a quarter note, written as a string (`"3"`, `"17/4"`). Seconds are derived from the tempo map and rounded to a microsecond. `t = 0` is sample 0 of the master. Both pieces tell time with `q` (performed quarters) so a different tempo is a recomputation, not a new card.

## Top level

| Key | Meaning |
|---|---|
| `schema`, `piece`, `title`, `licence` | Identity and the card's own licence (the Turca card is CC BY-NC-SA 4.0; see `NOTICE.md`) |
| `source` | `kind` (`kern` or `musicxml`), `path`, `sha256` of the file, edition, encoder, licence. The Score witness checks the hash |
| `meter` | `2/4` or `4/4` |
| `perform` | The conventions below, in words, plus the start tempo (`qpm`) |
| `tempo_map` | `[{q, bar, beat, qpm}]`, piecewise constant, first entry at `q = "0"`. The Ode's coda ritardando is one entry per quarter at whole `qpm`, so the map is exact |
| `key_map` | `[{t, q, key, section, rep}]`, a lower-case key is minor |
| `form` | One entry per pass of the performed form: `id`, `rep`, `bars` (first and last full bar), `q0`, `q1`, `t0`, `t1`, `label`; the Turca adds `wq0`, where the section starts in the written file |
| `instruments` | `[{id, layer, stem}]`; `layer` is `composer` or `arrangement` |
| `notes` | The notes, below |
| `harmony` | Chord segments, below |
| `checks` | The numbers the Score witness recomputes: `composer_note_heads`, `bars_performed`, `passes`, `quarters_performed`, `seconds`, `performed_notes`, `grace_notes`, `midi_range` |

## Notes

| Field | Meaning |
|---|---|
| `id` | `<piece>.<section><rep>.<instrument>.<voice>.<counter>`, for example `turca.A1.pno.R.0001`. The **last digit of the second part is the rep**, so `turca.I11...` is the first ending (section `I1`) in its first pass, while `turca.I2...` is section `I` in its second pass. The counter runs 1..n in performed order inside one (section pass, voice) |
| `inst`, `voice`, `layer` | Instrument id; `R` right hand, `R2` the right hand's second voice while it is split, `L` left hand (Turca), `M` melody (Ode); `composer` or `arrangement` |
| `pitch` | MIDI pitch **as written in the source** |
| `vel` | MIDI velocity from the dynamics (performance, not source) |
| `t`, `dur` | Performed onset and length in seconds. `dur` is the notated length; articulation is the renderer's business. A grace note's `t` is before the beat by its place in the group and its `dur` is one 32nd |
| `q`, `ql` | Performed onset and notated length in quarters, exact. A grace note has `ql = "0"` and the `q` of the note it decorates |
| `bar`, `beat` | Position on the performed grid: beat 1 is the downbeat, fractions are subdivisions. The Turca's upbeat is bar 0, beat 2, and a repeat sign closes bar 8 with the next pass's upbeat; the Ode counts bars from 1 |
| `section`, `rep` | The form pass the note belongs to |
| `src` | Where in the source: Turca `line:column` or `line:column.chordpos` of `sources/sonata11-3.krn` (1-based, physical tab column); Ode `m<measure>.<position>` in the MusicXML, `m12.4+m13.1` for a tied pair |
| `kbar` | The source's own bar number (the Ode: the bar of the 16-bar theme). A later upbeat keeps the number of the bar it completes |
| `g` | 1 for a grace note |
| `art` | Letters: `s` staccato, `a` arpeggiated chord, `t` trill |
| `sl` | `s` a slur starts here, `e` it ends here, `se` both |
| `oct` | Ode only: octaves between the written pitch and where the arrangement sounds the melody |
| `tied` | Ode only: written heads merged into this note |

## Harmony

`{t, dur, q, ql, key, roman, root, qual, pcs, bass, tension, section, rep}`. `qual` is `M`, `m`, `o` (diminished), `7` or `o7`. `roman` carries inversion figures (`V65`, `i6`). `tension` is the distance on Chew's spiral array between the chord's centre and the key's centre (r = 1, h = 0.365; chord weights 0.516, 0.315, 0.168 for root, fifth, third; key weights 0.536, 0.274, 0.190 for I, V, IV). Segments run without a gap from `q = 0` to the end.

## Feature tracks `loomsong.tracks/1`

`tracks/<piece>.tracks.json`: 60 Hz, `t = k / 60` seconds, the card's sha256 recorded. Ten channels (beat phase, bar phase, section, harmony index, tension, density, contour, low, high, active), each int16 little-endian in base64 with a `scale`. They are stored uncompressed so the file's bytes do not depend on the zlib that wrote it; `score/tracks.py:page_part` makes the gzip-plus-base64 parts the page decodes with `DecompressionStream`.

## What the Score witness checks

`witnesses/score_check.py` re-derives the expected composer notes from the source with a different parser from the builder's (music21, plus a line reader that follows the left-hand column only) and compares exactly: S0 source hash; S1 the notes (pitch, onset, length as exact fractions, section, rep: 0 missing, 0 extra); S2 the form against the file's own plan and the spec's table; S3 head counts, `src` pointers, bars performed; S4 seconds against the tempo map, grace times included; S5 bar, beat and `kbar`; S6 ids; S7 harmony; S8 key map; S10 layers; T0 to T2 the tracks. `witnesses/test_score_check.py` damages a card 19 ways and requires a red result each time.
