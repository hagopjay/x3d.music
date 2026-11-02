#!/usr/bin/env python3
"""Tests for the audio code: the meters, the mix's building blocks, the limiter, the sampler's pure parts and its playing rules (on synthetic samples), the rack's routing, and every Faust voice.

    python3 -I audio/test_audio.py            (about a minute; the Faust tests need DawDreamer and are skipped without it)

None of this needs the Salamander samples: the sampler runs on a folder of synthetic sine "recordings" made here. The finished masters are judged by the Ear witness (witnesses/ear.py), not here.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import meter, mix, rack, recipes, sampler  # noqa: E402
from pedalboard import Pedalboard  # noqa: E402

SR = meter.SR
HAVE_DAW = importlib.util.find_spec("dawdreamer") is not None


def noise(seconds, amp, seed=1, channels=2):
    return (np.random.default_rng(seed).standard_normal((int(seconds * SR), channels)) * amp).astype("float32")


class Meters(unittest.TestCase):
    def test_true_peak_sees_what_the_samples_miss(self):
        n = np.arange(SR)
        x = np.sin(2 * np.pi * (SR / 4) * n / SR + np.pi / 4)           # every sample is +-0.707; the wave between them reaches 1.0
        ramp = np.hanning(9600)[:4800]
        x[:4800] *= ramp                                                  # a tone that starts and stops abruptly makes the oversampling filter ring at its ends; real masters fade
        x[-4800:] *= ramp[::-1]
        self.assertAlmostEqual(meter.sample_peak_db(x), -3.01, places=1)
        self.assertGreater(meter.true_peak_db(x[:, None]), -0.15)
        self.assertLess(meter.true_peak_db(x[:, None]), 0.1)

    def test_correlation_of_identical_inverted_and_independent_channels(self):
        a = noise(5, 0.1, 1, 1)[:, 0]
        self.assertAlmostEqual(meter.stereo_correlation(np.stack([a, a], 1)), 1.0, places=3)
        self.assertAlmostEqual(meter.stereo_correlation(np.stack([a, -a], 1)), -1.0, places=3)
        self.assertLess(abs(meter.stereo_correlation(noise(10, 0.1, 2))), 0.05)

    def test_a_100_hz_tone_sits_in_the_bass_band(self):
        x = np.sin(2 * np.pi * 100 * np.arange(4 * SR) / SR).astype("float32")
        b = meter.band_levels(x)
        self.assertEqual(b["bass 60-250"], 0.0)
        self.assertTrue(all(v < -30 for k, v in b.items() if k != "bass 60-250"), b)

    def test_active_rms_reads_the_playing_level_not_the_average_over_silence(self):
        x = np.zeros(4 * SR, dtype="float32")
        x[SR:2 * SR] = 0.1 * np.sin(2 * np.pi * 440 * np.arange(SR) / SR)
        self.assertAlmostEqual(meter.active_rms_db(x), -23.0, delta=0.1)
        self.assertEqual(meter.active_rms_db(np.zeros(SR)), -120.0)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is not installed")
    def test_loudness_agrees_with_ffmpeg_on_music_like_noise(self):
        x = noise(20, 0.05) * np.linspace(0.3, 1.0, 20 * SR, dtype="float32")[:, None]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.wav")
            sf.write(p, x, SR, subtype="PCM_24")
            e = meter.ebur128(p)
        self.assertAlmostEqual(meter.lufs(x), e["I"], delta=0.1)
        self.assertAlmostEqual(meter.true_peak_db(x), e["TP"], delta=0.3)


class Curves(unittest.TestCase):
    def test_ducking_dips_at_the_kick_and_recovers(self):
        g = mix.duck_curve(2 * SR, [0.5], depth=0.3)
        self.assertAlmostEqual(float(g[int(0.5 * SR)]), 0.7, places=5)
        self.assertEqual(float(g[0]), 1.0)
        self.assertGreater(float(g[int((0.5 + 5 * 0.12) * SR)]), 0.995)
        both = mix.duck_curve(2 * SR, [0.5, 0.52], depth=0.3)
        self.assertAlmostEqual(float(both[int(0.52 * SR)]), 0.7, places=5)           # overlapping kicks take the deeper dip, they do not add up

    def test_the_gate_opens_on_the_hit_holds_and_closes(self):
        g = mix.gate_curve(2 * SR, [0.5])
        i = int(0.5 * SR)
        self.assertEqual(float(g[i - 1]), 0.0)
        self.assertEqual(float(g[i]), 1.0)
        self.assertEqual(float(g[i + int(0.17 * SR) - 1]), 1.0)
        self.assertEqual(float(g[i + int((0.17 + 0.045) * SR) + 2]), 0.0)
        self.assertGreater(float(g[i + int(0.17 * SR) + 10]), 0.9)

    def test_predelay_shifts_by_whole_samples_and_zero_changes_nothing(self):
        x = noise(1, 0.1)
        y = mix.predelay(x, 0.01)
        self.assertEqual(len(y), len(x))
        self.assertTrue(np.all(y[:480] == 0))
        self.assertTrue(np.array_equal(y[480:], x[:-480]))
        self.assertIs(mix.predelay(x, 0.0), x)

    def test_balance_turns_down_only_the_far_channel(self):
        one = np.ones((4, 2), dtype="float32")
        self.assertEqual(mix.balance(one, 1.0).tolist(), [[0.0, 1.0]] * 4)
        self.assertEqual(mix.balance(one, -1.0).tolist(), [[1.0, 0.0]] * 4)
        self.assertEqual(mix.balance(one, 0.5).tolist(), [[0.5, 1.0]] * 4)
        self.assertEqual(mix.balance(one, 0.0).tolist(), one.tolist())

    def test_normalise_brings_the_playing_blocks_to_the_reference(self):
        x = np.zeros((6 * SR, 2), dtype="float32")
        x[SR:3 * SR] = noise(2, 0.01)
        self.assertAlmostEqual(meter.active_rms_db(mix.normalise(x)), mix.REF_DB, delta=0.05)
        z = np.zeros((SR, 2), dtype="float32")
        self.assertIs(mix.normalise(z), z)


class Ride(unittest.TestCase):
    def test_every_pass_reaches_the_loudness_the_arc_asks_for(self):
        x = np.concatenate([noise(8, 0.05, 1), noise(8, 0.2, 2), noise(2, 0.2, 3)])
        form = [dict(id="A", rep=1, t0=0.0, t1=8.0), dict(id="B", rep=1, t0=8.0, t1=16.0)]
        y, rides = mix.ride(x, form, {"A1": -24.0, "B1": -18.0})
        self.assertAlmostEqual(meter.lufs(y[SR:7 * SR]), -24.0, delta=0.3)
        self.assertAlmostEqual(meter.lufs(y[9 * SR:15 * SR]), -18.0, delta=0.3)
        self.assertAlmostEqual(meter.lufs(y[16 * SR + SR // 2:]), -18.0, delta=0.5)          # the ring-out keeps the last ride
        self.assertEqual(set(rides), {"A1", "B1"})

    def test_a_pass_shorter_than_two_seconds_keeps_the_ride_before_it(self):
        x = noise(13, 0.1)
        form = [dict(id="A", rep=1, t0=0.0, t1=6.0), dict(id="B", rep=1, t0=6.0, t1=6.5), dict(id="C", rep=1, t0=6.5, t1=13.0)]
        _, rides = mix.ride(x, form, {"A1": -20.0, "B1": -10.0, "C1": -20.0})
        self.assertEqual(rides["B1"], rides["A1"])


class Limiter(unittest.TestCase):
    def test_music_under_the_ceiling_is_returned_untouched(self):
        x = noise(3, 0.05)
        y, g = mix.limit(x, -1.5)
        self.assertIs(y, x)
        self.assertEqual(float(g.min()), 1.0)

    def test_the_true_peak_ends_at_or_under_the_ceiling(self):
        t = np.arange(8 * SR) / SR
        x = (0.7 * np.sin(2 * np.pi * 220 * t))[:, None] + noise(8, 0.2, 5)
        for at in (2.0, 4.0, 4.005):                                                      # three bursts, the last two close together
            i = int(at * SR)
            x[i:i + 96] += (1.5 * np.sin(2 * np.pi * 1000 * np.arange(96) / SR))[:, None]
        x = x.astype("float32")
        self.assertGreater(meter.true_peak_db(x), 3.0)
        y, g = mix.limit(x, -1.5)
        self.assertLessEqual(meter.true_peak_db(y), -1.5 + 0.02)
        self.assertLessEqual(float(g.max()), 1.0 + 1e-9)

    def test_it_has_no_latency_and_turns_down_before_a_peak_and_not_after(self):
        x = np.zeros((6 * SR, 2), dtype="float32")
        x[SR, :] = 1.0                                                                    # one-sample click
        y, g = mix.limit(x, -1.5)
        self.assertEqual(int(np.argmax(np.abs(y[:, 0]))), SR)
        self.assertLessEqual(float(np.abs(y).max()), 10 ** (-1.5 / 20) + 1e-6)
        self.assertTrue(np.allclose(g[:SR - 400], 1.0, atol=1e-9))                       # nothing is turned down before the look-ahead window
        self.assertLess(float(g[SR - 50]), 1.0)                                           # the gain is already down just before the click
        self.assertGreater(float(g[5 * SR]), 0.9999)                                      # and has recovered long after it

    def test_a_quiet_passage_far_from_a_peak_is_not_changed(self):
        x = np.concatenate([noise(3, 0.02, 1), noise(2, 0.9, 2), noise(3, 0.02, 3)])
        y, _ = mix.limit(x, -1.5)
        self.assertTrue(np.array_equal(y[:2 * SR], x[:2 * SR]))
        self.assertLess(float(np.abs(y[-2 * SR:] - x[-2 * SR:]).max()), 1e-4)

    def test_leaky_max_equals_the_definition(self):
        a = np.abs(np.random.default_rng(3).standard_normal(3000))
        d = 0.99
        want = np.array([max(a[n - k] * d ** k for k in range(n + 1)) for n in range(len(a))])
        self.assertTrue(np.allclose(mix.leaky_max(a, d), want, rtol=1e-9, atol=1e-12))

    def test_the_cheap_true_peak_equals_the_full_oversampling_where_it_matters(self):
        from scipy import signal
        x = noise(3, 0.4, 9)
        x[SR:SR + 2000] *= 2.0
        floor = 0.8
        cheap = mix.true_peak_envelope(x, floor)
        over = np.abs(signal.resample_poly(x, 4, 1, axis=0, padtype="line"))
        full = np.maximum(over[:, 0], over[:, 1]).reshape(-1, 4).max(axis=1)
        hot = np.flatnonzero(np.maximum(np.abs(x[:, 0]), np.abs(x[:, 1])) > floor)
        hot = hot[(hot > 100) & (hot < len(x) - 100)]
        self.assertGreater(len(hot), 50)
        self.assertLess(float(np.abs(cheap[hot] - full[hot]).max()), 2e-3)
        self.assertTrue(np.all(cheap >= np.maximum(np.abs(x[:, 0]), np.abs(x[:, 1])) - 1e-9))

    def test_the_master_lands_on_minus_14_with_the_peak_under_the_ceiling(self):
        x = noise(12, 0.03, 4) * (1.0 + 4.0 * (np.random.default_rng(5).random((12 * SR, 1)) > 0.9995)).astype("float32")
        y, report = mix.master(x, {"master_chain": lambda: Pedalboard([])})
        self.assertAlmostEqual(meter.lufs(y), -14.0, delta=0.05)
        self.assertLessEqual(meter.true_peak_db(y), -1.5 + 0.02)
        self.assertIn("max_reduction_db", report)


class Spaces(unittest.TestCase):
    def test_the_return_trims_are_the_measured_ones(self):
        measured = mix.calibrate_spaces()
        for k, v in mix.SPACE_TRIM_DB.items():
            self.assertAlmostEqual(-measured[k], v, delta=0.05, msg=k)


class Recipes(unittest.TestCase):
    def setUp(self):
        self.cards = {}
        for p in ("turca", "ode"):
            with open(os.path.join(ROOT, "score", p + ".score.json")) as f:
                self.cards[p] = json.load(f)

    def test_every_instrument_on_a_card_has_a_voice_and_a_recipe_stem(self):
        for p, card in self.cards.items():
            by = rack.instrument_notes(card)
            for inst in by:
                self.assertTrue(inst == "pno" or inst in rack.RACK, "%s: no voice for %s" % (p, inst))
                self.assertIn(inst, recipes.RECIPES[p]["stems"], "%s: no recipe stem for %s" % (p, inst))
            for inst in recipes.RECIPES[p]["stems"]:
                self.assertIn(inst, by, "%s: the recipe mixes %s but the card never plays it" % (p, inst))

    def test_the_arc_names_exactly_the_passes_long_enough_to_ride(self):
        for p, card in self.cards.items():
            long_enough = {"%s%d" % (f["id"], f["rep"]) for f in card["form"] if f["t1"] - f["t0"] >= 2.0}
            self.assertEqual(set(recipes.RECIPES[p]["arc"]), long_enough, p)

    def test_every_chain_passes_a_click_without_delaying_it(self):
        x = np.zeros((SR, 2), dtype="float32")
        x[2000, :] = 0.5
        for p, r in recipes.RECIPES.items():
            for inst, s in r["stems"].items():
                y = mix.run(s["chain"](), x)
                self.assertLessEqual(abs(int(np.argmax(np.abs(y[:, 0]))) - 2000), 48, "%s %s delays a click by more than 1 ms" % (p, inst))
                self.assertTrue(np.isfinite(y).all(), "%s %s" % (p, inst))

    def test_every_stem_with_a_level_names_a_crest_and_a_sane_send_set(self):
        for p, r in recipes.RECIPES.items():
            for inst, s in r["stems"].items():
                self.assertIn("level", s, "%s %s" % (p, inst))
                for space in s.get("sends", {}):
                    self.assertIn(space, mix.SPACES, "%s %s sends to an unknown space %s" % (p, inst, space))
                self.assertLessEqual(abs(s.get("pan", 0.0)), 1.0)


class Routing(unittest.TestCase):
    def card(self):
        def n(t, pitch, inst, layer, section, **kw):
            return dict(t=t, dur=0.5, pitch=pitch, vel=80, inst=inst, layer=layer, section=section, **kw)
        return dict(
            routing={"mel": {"S1": [dict(inst="bass", rel=-1, vel=6)], "S2": [dict(inst="strings", rel=0, vel=-6), dict(inst="ep", rel=1, vel=0, dur=0.5)]}},
            notes=[n(0, 64, "mel", "composer", "S1", oct=-1), n(1, 64, "mel", "composer", "S2", oct=0), n(2, 64, "mel", "composer", "Coda"), n(0, 36, "kick", "arrangement", "S1")])

    def test_composer_notes_go_to_the_instruments_the_section_names_with_their_octave_and_velocity(self):
        by = rack.instrument_notes(self.card())
        self.assertEqual([x["pitch"] for x in by["bass"]], [64 + 12 * (-1 - 1)])
        self.assertEqual([x["vel"] for x in by["bass"]], [86])
        self.assertEqual([x["pitch"] for x in by["strings"]], [64])
        self.assertEqual([x["vel"] for x in by["strings"]], [74])
        self.assertEqual([x["pitch"] for x in by["ep"]], [76])
        self.assertEqual([x["dur"] for x in by["ep"]], [0.25])                           # a route may shorten the note

    def test_a_section_with_no_route_stays_silent_and_the_arrangement_is_untouched(self):
        by = rack.instrument_notes(self.card())
        self.assertEqual(sorted(by), ["bass", "ep", "kick", "strings"])
        self.assertEqual([x["pitch"] for x in by["kick"]], [36])

    def test_velocity_is_kept_inside_the_midi_range(self):
        c = self.card()
        c["routing"]["mel"]["S1"] = [dict(inst="bass", rel=0, vel=100)]
        self.assertEqual(rack.instrument_notes(c)["bass"][0]["vel"], 127)
        c["routing"]["mel"]["S1"] = [dict(inst="bass", rel=0, vel=-100)]
        self.assertEqual(rack.instrument_notes(c)["bass"][0]["vel"], 1)

    def test_a_card_without_routing_plays_its_notes_where_they_are(self):
        by = rack.instrument_notes(dict(notes=[dict(t=0, dur=1, pitch=60, vel=70, inst="pno", layer="composer", section="A")]))
        self.assertEqual(list(by), ["pno"])


class SamplerRules(unittest.TestCase):
    def test_a_note_takes_the_nearest_key_and_is_never_shifted_more_than_a_semitone_inside_the_range(self):
        self.assertEqual(sampler.key_for(60), ("C4", 60))
        self.assertEqual(sampler.key_for(61), ("C4", 60))
        self.assertEqual(sampler.key_for(62), ("D#4", 63))
        for m in range(39, 88):
            self.assertLessEqual(abs(m - sampler.key_for(m)[1]), 1, m)
        self.assertEqual(sampler.key_for(100)[0], "D#6")
        self.assertEqual(sampler.key_for(20)[0], "D#2")

    def test_velocity_blends_the_two_recorded_layers_either_side(self):
        self.assertEqual(sampler.layer_blend(1), [(2, 1.0)])
        self.assertEqual(sampler.layer_blend(127), [(16, 1.0)])
        (la, wa), (lb, wb) = sampler.layer_blend(34)
        self.assertEqual((la, lb), (2, 4))
        self.assertAlmostEqual(wa, 0.6)
        self.assertAlmostEqual(wb, 0.4)
        prev = None
        for v in range(1, 128):
            b = sampler.layer_blend(v)
            self.assertAlmostEqual(sum(w for _, w in b), 1.0)
            self.assertLessEqual(len(b), 2)
            amp = sum(w * sampler.LAYERS[l] for l, w in b)                                # the blend's "effective velocity" rises smoothly with the velocity
            if prev is not None:
                self.assertGreaterEqual(amp, prev - 1e-9)
                self.assertLessEqual(amp - prev, 1.01)
            prev = amp

    def test_release_times(self):
        self.assertEqual(sampler.release_seconds(95), 0.5)                                # no dampers up there
        self.assertEqual(sampler.release_seconds(40), 0.45)
        self.assertEqual(sampler.release_seconds(70), 0.22)
        self.assertEqual(sampler.release_seconds(40, staccato=True), 0.09)
        self.assertEqual(sampler.release_seconds(70, staccato=True), 0.09)

    def test_a_slur_holds_every_note_inside_it_and_not_the_last(self):
        notes = [dict(t=0, pitch=60, sl="s", voice="a"), dict(t=1, pitch=62, voice="a"), dict(t=2, pitch=64, sl="e", voice="a"), dict(t=3, pitch=65, voice="a"),
                 dict(t=0.5, pitch=48, voice="b"), dict(t=1.5, pitch=50, sl="se", voice="b"), dict(t=2.5, pitch=52, sl="e", voice="b")]
        self.assertEqual(sampler.Grand.legato_flags(notes), [True, True, False, False, False, True, False])


class SamplerOnSyntheticRecordings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="loomsong-samples-")
        t = np.arange(int(1.4 * SR)) / SR
        for key, midi in sampler.KEYS.items():
            f = 440.0 * 2 ** ((midi - 69) / 12)
            for layer in sampler.LAYERS:
                x = np.sin(2 * np.pi * f * t) * np.exp(-1.2 * t) * (0.1 + 0.03 * layer)
                sf.write(os.path.join(cls.dir, "%sv%d.flac" % (key, layer)), np.stack([x, x], 1).astype("float32"), SR, subtype="PCM_24")
        cls.grand = sampler.Grand(cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_a_note_lasts_its_hold_plus_its_release_and_ends_at_exactly_zero(self):
        a = self.grand.note(60, 90, 0.5)
        self.assertEqual(len(a), int(round(0.5 * SR)) + int(round(sampler.release_seconds(60) * SR)))
        self.assertEqual(float(np.abs(a[-1]).max()), 0.0)
        self.assertEqual(float(np.abs(a[0]).max()), 0.0)                                  # the first sample is zero: the 1 ms fade-in, no click

    def test_the_first_sound_of_a_note_is_at_its_written_time(self):
        out = self.grand.render([dict(t=1.0, dur=0.5, pitch=60, vel=80)], 3.0)
        self.assertEqual(len(out), 3 * SR)
        self.assertTrue(np.all(out[:SR] == 0))
        first = int(np.argmax(np.abs(out[:, 0]) > 0))
        self.assertGreaterEqual(first, SR)
        self.assertLess(first, SR + 100)

    def test_a_pitch_off_the_key_is_shifted_the_right_way_by_the_right_amount(self):
        for midi in (61, 62, 66):
            out = self.grand.note(midi, 90, 0.8)[:, 0]
            spec = np.abs(np.fft.rfft(out[:int(0.4 * SR)] * np.hanning(int(0.4 * SR)), n=1 << 18))
            peak = np.argmax(spec) * SR / (1 << 18)
            self.assertAlmostEqual(peak / (440.0 * 2 ** ((midi - 69) / 12)), 1.0, delta=0.005, msg=midi)

    def test_louder_means_louder(self):
        rms = lambda v: float(np.sqrt((self.grand.note(60, v, 0.5) ** 2).mean()))
        self.assertGreater(rms(100), rms(70))
        self.assertGreater(rms(70), rms(40))

    def test_a_rolled_chord_starts_each_voice_18_ms_after_the_one_below(self):
        low = dict(t=1.0, dur=0.5, pitch=60, vel=80, art="a")
        high = dict(t=1.0, dur=0.5, pitch=64, vel=80, art="a")
        both = self.grand.render([high, low], 3.0)
        alone = self.grand.render([low], 3.0) + self.grand.render([dict(high, t=1.018)], 3.0)
        self.assertTrue(np.allclose(both, alone, atol=1e-6))

    def test_staccato_grace_and_slurred_notes_sound_for_the_lengths_the_docstring_gives(self):
        def placed(nt, sounding, stac=False):
            want = np.zeros((3 * SR + 4 * SR, 2), dtype="float32")
            audio = self.grand.note(nt["pitch"], nt["vel"], max(sounding, 0.03), stac)
            i0 = int(round(nt["t"] * SR))
            want[i0:i0 + len(audio)] += audio
            return want[:3 * SR]
        base = dict(t=1.0, dur=0.5, pitch=60, vel=80)
        self.assertTrue(np.allclose(self.grand.render([dict(base, art="s")], 3.0), placed(base, 0.14, True)))
        self.assertTrue(np.allclose(self.grand.render([dict(base, art="s", dur=0.2)], 3.0), placed(dict(base, dur=0.2), 0.09, True)))
        self.assertTrue(np.allclose(self.grand.render([dict(base, g=True)], 3.0), placed(base, 0.52)))
        self.assertTrue(np.allclose(self.grand.render([dict(base)], 3.0), placed(base, 0.47)))
        slurred = [dict(base, sl="s", voice="a"), dict(base, t=2.0, sl="e", voice="a")]
        want = placed(slurred[0], 0.53) + placed(slurred[1], 0.47)
        self.assertTrue(np.allclose(self.grand.render(slurred, 3.5)[:3 * SR], want, atol=1e-6))

    def test_two_renders_are_identical(self):
        notes = [dict(t=0.2 * i, dur=0.3, pitch=55 + 3 * i, vel=60 + 5 * i) for i in range(8)]
        self.assertTrue(np.array_equal(self.grand.render(notes, 4.0), self.grand.render(notes, 4.0)))


@unittest.skipUnless(HAVE_DAW, "DawDreamer is not installed")
class FaustVoices(unittest.TestCase):
    def test_every_voice_compiles_sounds_and_starts_on_its_note(self):
        for inst in sorted(rack.RACK):
            out = rack.render_faust(inst, [dict(pitch=48, vel=100, t=0.1, dur=0.4)], 1.5)
            self.assertEqual(out.shape, (int(1.5 * SR), 2), inst)
            self.assertTrue(np.isfinite(out).all(), inst)
            peak = float(np.abs(out).max())
            self.assertGreater(peak, 1e-3, "%s is silent" % inst)
            self.assertLess(peak, 8.0, "%s is absurdly loud before its chain (%.1f)" % (inst, peak))
            self.assertEqual(float(np.abs(out[:int(0.1 * SR)]).max()), 0.0, "%s sounds before its note" % inst)

    def test_a_note_starts_on_the_exact_sample(self):
        for t in (0.5, 0.5 + 1.0 / 3 / 100, 0.731):
            out = rack.render_faust("kick", [dict(pitch=36, vel=100, t=t, dur=0.2)], 2.0)[:, 0]
            first = int(np.argmax(np.abs(out) > 0))
            self.assertLessEqual(abs(first - t * SR), 1.0, "kick written at %.5f s starts at sample %d" % (t, first))

    def test_two_renders_are_identical_on_one_machine(self):
        notes = [dict(pitch=40 + 2 * i, vel=70 + 3 * i, t=0.1 + 0.25 * i, dur=0.2) for i in range(6)]
        a = rack.render_faust("strings", notes, 3.0)
        self.assertTrue(np.array_equal(a, rack.render_faust("strings", notes, 3.0)))

    def test_more_notes_than_voices_do_not_break_it(self):
        notes = [dict(pitch=36, vel=100, t=0.05 * i, dur=0.1) for i in range(40)]            # the kick has four voices
        out = rack.render_faust("kick", notes, 3.0)
        self.assertTrue(np.isfinite(out).all())
        self.assertGreater(float(np.abs(out).max()), 1e-3)


if __name__ == "__main__":
    unittest.main(verbosity=1)
