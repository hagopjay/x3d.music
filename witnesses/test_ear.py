"""The Ear witness must pass a good master and go red on every kind of bad one: a witness that cannot fail proves nothing.

The fixture is a 30 s synthetic piece (kick, snare, a piano-like voice with a 2 ms attack, a stereo pad and a reverb-like return), mixed to -14 LUFS under the same limiter as the real mixes, with a fake card that
lists where each hit is. Each test damages a copy and names the checks that must turn red. Needs numpy, scipy, soundfile, pyloudnorm, pedalboard and ffmpeg (requirements-audio.txt).
"""
import os, shutil, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "audio"))
try:
    import numpy as np
    import soundfile as sf
    from scipy import signal
    import ear
    import meter
    import mix
    AVAILABLE = shutil.which("ffmpeg") is not None
except ImportError:
    AVAILABLE = False
SKIP = "the audio requirements (numpy, scipy, soundfile, pyloudnorm, pedalboard, ffmpeg) are not installed (the CI audio job installs requirements-audio.txt)"

SR = 48000
SECONDS = 30.0
KICKS = [0.5 + 0.5 * k for k in range(58)]
SNARES = [0.75 + 1.0 * k for k in range(29)]
PIANOS = [1.0 + 0.7 * k for k in range(40)]


def burst(rng, n, kind):
    t = np.arange(n) / SR
    if kind == "kick":
        return 0.8 * (np.sin(2 * np.pi * (55 + 70 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.08) + 0.5 * rng.standard_normal(n) * np.exp(-t / 0.003))
    if kind == "snare":
        return 0.6 * np.diff(rng.standard_normal(n + 1)) * np.exp(-t / 0.06)
    raise ValueError(kind)


def piano_note(rng, f, n, attack=0.002):
    t = np.arange(n) / SR
    tone = sum(w * np.sin(2 * np.pi * f * k * t) for k, w in ((1, 1.0), (2, 0.5), (3, 0.3), (4, 0.2)))
    return 0.35 * (np.minimum(t / attack, 1.0) * np.exp(-t / 0.5) * tone + 0.25 * rng.standard_normal(n) * np.exp(-t / 0.012))


def place(track, times, make, rng):
    for k, t in enumerate(times):
        i = int(round(t * SR))
        m = min(int(0.7 * SR), len(track) - i)
        track[i:i + m] += make(rng, k, int(0.7 * SR))[:m]


def build(folder):
    """Write master + stems into folder; return the fake card."""
    rng = np.random.default_rng(3)
    n = int(SECONDS * SR)
    kick, snare, pno = np.zeros(n), np.zeros(n), np.zeros(n)
    place(kick, KICKS, lambda r, k, m: burst(r, m, "kick"), rng)
    place(snare, SNARES, lambda r, k, m: burst(r, m, "snare"), rng)
    place(pno, PIANOS, lambda r, k, m: piano_note(r, 220.0 * 2 ** ((k * 5 % 24) / 12.0), m), rng)

    def lowpassed(amp):
        out = []
        for _ in range(2):
            x = signal.lfilter([0.1], [1, -0.9], rng.standard_normal(n))
            out.append(amp * x * (0.6 + 0.4 * np.sin(2 * np.pi * 0.2 * np.arange(n) / SR)))
        return np.stack(out, axis=1)

    hp = signal.butter(4, 70.0, "highpass", fs=SR, output="sos")
    stems = {"kick": np.stack([kick, kick], axis=1), "snare": np.stack([snare, snare], axis=1), "pno": np.stack([pno, pno], axis=1), "pad": lowpassed(0.5), "fx_hall": lowpassed(0.25)}
    t = np.arange(n) / SR
    level = (np.where(t < 15.0, 1.0, 2.8) * np.clip((SECONDS - t) / 2.0, 0.0, 1.0))[:, None]   # a quiet half and a loud half, so the loudness range is real; a two-second fade at the end
    stems = {k: signal.sosfilt(hp, v, axis=0) * level for k, v in stems.items()}
    k = 0.9 / max(np.abs(v).max() for v in stems.values())
    stems = {name: v * k for name, v in stems.items()}
    total = sum(stems.values())
    gain = 10 ** ((-14.0 - meter.lufs(total)) / 20)
    for _ in range(6):
        out, _g = mix.limit((total * gain).astype("float32"), -1.5)
        gain *= 10 ** ((-14.0 - meter.lufs(out)) / 20)
    os.makedirs(os.path.join(folder, "stems"))
    for name, v in stems.items():
        sf.write(os.path.join(folder, "stems", name + ".wav"), v, SR, subtype="PCM_24")
    sf.write(os.path.join(folder, "master.wav"), out, SR, subtype="PCM_24")
    notes = [{"inst": i, "t": t, "layer": "arrangement"} for i, ts in (("kick", KICKS), ("snare", SNARES), ("pno", PIANOS)) for t in ts]
    return {"checks": {"seconds": SECONDS}, "instruments": [{"id": i, "layer": "arrangement", "stem": "stems/%s.wav" % i} for i in ("kick", "snare", "pno")], "notes": notes}


# the fixture's piano has a hammer-noise onset, so it reads like an impulsive hit; the detector window that fits the real sampler's piano (ear.PIANO) is checked on the real stems in the CI audio job
STEMS = (("pno", ear.IMPULSIVE), ("kick", ear.IMPULSIVE), ("snare", ear.IMPULSIVE)) if AVAILABLE else None
_BASE = {}


def setUpModule():
    if AVAILABLE:
        _BASE["dir"] = tempfile.mkdtemp(prefix="ear-base-")
        _BASE["card"] = build(_BASE["dir"])


def tearDownModule():
    if _BASE.get("dir"):
        shutil.rmtree(_BASE["dir"], ignore_errors=True)


@unittest.skipIf(not AVAILABLE, SKIP)
class EarWitness(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ear-case-")
        shutil.copytree(_BASE["dir"], self.dir, dirs_exist_ok=True)
        self.card = _BASE["card"]
        self.master = os.path.join(self.dir, "master.wav")
        self.stems = os.path.join(self.dir, "stems")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def red(self):
        return {r["id"] for r in ear.check(self.card, "test", self.master, self.stems, onset_stems=STEMS) if not r["ok"]}

    def read_master(self):
        return sf.read(self.master, dtype="float64")[0]

    def write_master(self, x, sr=SR):
        sf.write(self.master, x, sr, subtype="PCM_24")

    def edit_stem(self, name, f):
        p = os.path.join(self.stems, name + ".wav")
        x, _ = sf.read(p, dtype="float64")
        sf.write(p, f(x), SR, subtype="PCM_24")

    def test_a_good_master_passes_everything(self):
        res = ear.check(self.card, "test", self.master, self.stems, onset_stems=STEMS)
        self.assertEqual([r for r in res if not r["ok"]], [], "\n".join("%s %s" % (r["id"], r["detail"]) for r in res if not r["ok"]))
        self.assertEqual(len(res), 10)

    def test_too_quiet(self):
        self.write_master(self.read_master() * 10 ** (-6 / 20))
        self.assertIn("E2", self.red())

    def test_too_loud(self):
        self.write_master(np.clip(self.read_master() * 10 ** (4 / 20), -0.89, 0.89))
        self.assertTrue({"E2", "E3"} <= self.red())

    def test_clipped(self):
        self.write_master(np.clip(self.read_master() * 4.0, -1.0, 1.0))
        self.assertTrue({"E3", "E5"} <= self.red())

    def test_a_clipped_stem(self):
        self.edit_stem("kick", lambda x: np.clip(x * 8.0, -1.0, 1.0))
        self.assertIn("E5", self.red())

    def test_a_stem_with_dc(self):
        self.edit_stem("pad", lambda x: x + 0.01)
        self.assertIn("E5", self.red())

    def test_right_channel_inverted(self):
        x = self.read_master()
        x[:, 1] = -x[:, 1]
        self.write_master(x)
        self.assertIn("E6", self.red())

    def test_stems_shifted_against_the_score(self):
        self.edit_stem("kick", lambda x: np.roll(x, int(0.040 * SR), axis=0))
        self.assertIn("E7", self.red())

    def test_snare_missing(self):
        os.remove(os.path.join(self.stems, "snare.wav"))
        self.assertIn("E7", self.red())

    def test_tempo_drift_of_one_percent(self):
        def stretch(x):
            idx = np.arange(len(x)) / 1.01
            return np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)
        self.edit_stem("kick", stretch)
        self.assertIn("E7", self.red())

    def test_the_piano_late_by_20_ms(self):
        self.edit_stem("pno", lambda x: np.roll(x, int(0.020 * SR), axis=0))
        self.assertIn("E7", self.red())

    def test_master_late_against_the_stems(self):
        self.write_master(np.roll(self.read_master(), int(0.010 * SR), axis=0))
        self.assertIn("E8", self.red())

    def test_master_that_is_not_made_from_these_stems(self):
        rng = np.random.default_rng(9)
        x = self.read_master()
        self.write_master(x * 0.2 + rng.standard_normal(x.shape) * 0.05)
        self.assertIn("E8", self.red())

    def test_wrong_sample_rate(self):
        x = self.read_master()
        self.write_master(signal.resample_poly(x, 441, 480, axis=0), sr=44100)
        self.assertIn("E1", self.red())

    def test_a_stem_of_another_length(self):
        self.edit_stem("pad", lambda x: x[:-1000])
        self.assertIn("E1", self.red())

    def test_master_shorter_than_the_card(self):
        self.write_master(self.read_master()[:int(20 * SR)])
        self.assertIn("E1", self.red())

    def test_flat_loudness_has_no_range(self):
        rng = np.random.default_rng(5)
        x = rng.standard_normal((int(SECONDS * SR), 2))
        x = signal.lfilter([0.3], [1, -0.7], x, axis=0)
        x = x * 10 ** ((-14.0 - meter.lufs(x)) / 20)
        out, _g = mix.limit(x.astype("float32"), -1.5)
        self.write_master(out)
        self.assertIn("E4", self.red())

    def test_sub_rumble(self):
        x = self.read_master()
        rumble = 0.25 * np.sin(2 * np.pi * 40.0 * np.arange(len(x)) / SR)
        self.write_master(np.clip(x + rumble[:, None], -0.89, 0.89))
        self.assertIn("E9", self.red())

    def test_cut_off_mid_ring(self):
        x = self.read_master()
        x[-int(0.2 * SR):] = 0.0
        x[-int(0.2 * SR) - 4800:-int(0.2 * SR)] = 0.2 * np.sin(2 * np.pi * 220.0 * np.arange(4800) / SR)[:, None]
        y = x.copy()
        y[-int(0.1 * SR):] = 0.05 * np.sin(2 * np.pi * 330.0 * np.arange(int(0.1 * SR)) / SR)[:, None]
        self.write_master(y)
        self.assertIn("E10", self.red())

    def test_nan_in_a_stem(self):
        p = os.path.join(self.stems, "pad.wav")
        x, _ = sf.read(p, dtype="float32")
        x[1000, 0] = np.nan
        sf.write(p, x, SR, subtype="FLOAT")                                                 # the only format that can hold it; the format check goes red too
        self.assertTrue({"E1", "E5"} <= self.red())


class Detector(unittest.TestCase):
    @unittest.skipIf(not AVAILABLE, SKIP)
    def test_impulsive_window_has_under_3_ms_bias_on_clicks(self):
        rng = np.random.default_rng(1)
        times = [0.5 + 0.4 * k for k in range(40)]
        x = np.zeros(int(18 * SR))
        for t in times:
            i = int(round(t * SR))
            x[i:i + 4000] += burst(rng, 4000, "snare")
        e = ear.onset_errors(x, np.array(times), **ear.IMPULSIVE)
        self.assertLess(abs(float(np.median(e))), 0.003)
        self.assertLess(float(np.percentile(np.abs(e), 95)), 0.004)

    @unittest.skipIf(not AVAILABLE, SKIP)
    def test_both_windows_follow_a_shift_of_20_ms(self):
        """Whatever a window's bias on a sound, it moves one for one with the sound: the witness reads shifts, which is what a timing fault is."""
        rng = np.random.default_rng(2)
        times = np.array([0.5 + 0.6 * k for k in range(40)])
        x = np.zeros(int(26 * SR))
        for k, t in enumerate(times):
            i = int(round(t * SR))
            x[i:i + 30000] += piano_note(rng, 220.0 * 2 ** ((k * 5 % 24) / 12.0), 30000)
        for params in (ear.IMPULSIVE, ear.PIANO):
            e0 = float(np.median(ear.onset_errors(x, times, **params)))
            e1 = float(np.median(ear.onset_errors(x, times - 0.020, **params)))
            self.assertAlmostEqual(e1 - e0, 0.020, delta=0.002)

    @unittest.skipIf(not AVAILABLE, SKIP)
    def test_the_real_piano_stem_reads_within_the_tolerance(self):
        card_path = os.path.join(ROOT, "score", "turca.score.json")
        stem = os.path.join(ROOT, "build", "audio", "turca", "stems", "pno.wav")
        if not (os.path.exists(card_path) and os.path.exists(stem)):
            self.skipTest("the Turca piano stem has not been built here (python3 audio/render.py turca)")
        import json
        with open(card_path, encoding="utf-8") as f:
            card = json.load(f)
        x, _ = sf.read(stem, dtype="float32")
        e = np.abs(ear.onset_errors(x, ear.expected_onsets(card, "pno"), **ear.PIANO))
        self.assertLess(float(np.median(e)), ear.ONSET_MEDIAN_MS / 1000)
        self.assertLess(float(np.percentile(e, 95)), ear.ONSET_P95_MS / 1000)

    @unittest.skipIf(not AVAILABLE, SKIP)
    def test_expected_onsets_skip_graces_rolls_and_crowded_hits(self):
        card = {"notes": [{"inst": "p", "t": 1.0}, {"inst": "p", "t": 1.02}, {"inst": "p", "t": 2.0, "g": True}, {"inst": "p", "t": 3.0, "art": "a"}, {"inst": "p", "t": 4.0}, {"inst": "p", "t": 5.0}, {"inst": "q", "t": 9.0}]}
        self.assertEqual(list(ear.expected_onsets(card, "p")), [4.0, 5.0])


if __name__ == "__main__":
    unittest.main()
