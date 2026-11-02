"""A small sampler for the Salamander Grand Piano V3 (Alexander Holm, CC BY 3.0; see NOTICE.md).

Eight of the sixteen recorded velocity layers, 17 sampled keys (D#2 to D#6, three semitones apart). A note takes the nearest key, shifts it by resampling (at most one semitone), blends the
two recorded layers either side of its velocity, and ends with an exponential release when the key goes up. Deterministic: no random numbers. numpy, soundfile and soxr only.
"""
import os
import numpy as np
import soundfile as sf
import soxr

SR = 48000
KEYS = {"D#2": 39, "F#2": 42, "A2": 45, "C3": 48, "D#3": 51, "F#3": 54, "A3": 57, "C4": 60, "D#4": 63, "F#4": 66, "A4": 69, "C5": 72, "D#5": 75, "F#5": 78, "A5": 81, "C6": 84, "D#6": 87}
# The middle of the SFZ's velocity ranges for the layers we fetched: v2 27-34, v4 37-43, v6 47-50, v8 57-64, v10 73-80, v12 89-96, v14 105-112, v16 121-127.
LAYERS = {2: 30, 4: 40, 6: 48, 8: 60, 10: 76, 12: 92, 14: 108, 16: 124}
MAX_SECONDS = 9.0           # longer than any note the Turca holds; the tail is faded out
ATTACK_DB = -50.0           # the recorded files start with 2 to 17 ms of room tone: the note starts where the level first passes this under the file's peak
VEL_DB_PER_STEP = 0.10      # extra dynamics on top of the recorded layers (they span only about 6 dB between p and f): +0.1 dB per velocity step above 64


def cache_dir():
    base = os.environ.get("LOOMSONG_CACHE") or os.path.expanduser("~/.cache/loomsong")
    return os.path.join(base, "salamander", "Samples")


def key_for(midi):
    """The sampled key nearest a MIDI pitch (ties go to the lower key)."""
    return min(KEYS.items(), key=lambda kv: (abs(kv[1] - midi), kv[1]))


def layer_blend(vel):
    """[(layer, weight)] for a velocity: the two recorded layers either side of it, blended linearly in amplitude; outside the range the nearest layer alone."""
    items = sorted(LAYERS.items())
    if vel <= items[0][1]:
        return [(items[0][0], 1.0)]
    if vel >= items[-1][1]:
        return [(items[-1][0], 1.0)]
    for (la, ca), (lb, cb) in zip(items, items[1:]):
        if ca <= vel <= cb:
            w = (vel - ca) / (cb - ca)
            return [(la, 1.0 - w), (lb, w)]
    raise AssertionError("unreachable")


def release_seconds(midi, staccato=False):
    """How long the damper takes to still a note: short for staccato, longer in the bass, and the top notes (F#6 and above) have no dampers in the recording."""
    if midi >= 89:
        return 0.5
    base = 0.45 if midi < 52 else 0.22
    return min(base, 0.09) if staccato else base


class Grand:
    def __init__(self, directory=None):
        self.dir = directory or cache_dir()
        self._raw, self._shifted = {}, {}

    def _load(self, key, layer):
        k = (key, layer)
        if k not in self._raw:
            x, sr = sf.read(os.path.join(self.dir, "%sv%d.flac" % (key, layer)), dtype="float32")
            assert sr == SR and x.ndim == 2, "%s%d: expected 48 kHz stereo" % (key, layer)
            peak = float(np.abs(x).max())
            a = int(np.argmax(np.abs(x).max(axis=1) > peak * 10 ** (ATTACK_DB / 20)))
            x = x[a:a + int(MAX_SECONDS * SR)].copy()
            fade = int(1.5 * SR)
            if len(x) > fade:
                x[-fade:] *= np.linspace(1.0, 0.0, fade, dtype="float32")[:, None]
            x[:48] *= np.linspace(0.0, 1.0, 48, dtype="float32")[:, None]          # 1 ms in: no click where the file was cut
            self._raw[k] = x
        return self._raw[k]

    def sample(self, midi, layer):
        """The key nearest `midi` in `layer`, shifted to `midi` (cached)."""
        k = (midi, layer)
        if k not in self._shifted:
            key, centre = key_for(midi)
            x = self._load(key, layer)
            if midi != centre:
                ratio = 2.0 ** ((midi - centre) / 12.0)          # playing the recording faster by `ratio` raises it by that many semitones
                x = soxr.resample(x, SR, SR / ratio, quality="HQ").astype("float32")
            self._shifted[k] = x
        return self._shifted[k]

    def note(self, midi, vel, sounding, staccato=False):
        """The audio of one note held for `sounding` seconds, then released: float32 array (n, 2), starting exactly at the attack."""
        rel = release_seconds(midi, staccato)
        n_hold, n_rel = int(round(sounding * SR)), int(round(rel * SR))
        n = n_hold + n_rel
        out = np.zeros((n, 2), dtype="float32")
        for layer, w in layer_blend(vel):
            x = self.sample(midi, layer)[:n]
            out[:len(x)] += w * x
        env = np.ones(n, dtype="float32")
        if n_rel:
            env[n_hold:] = np.exp(-6.9078 * np.arange(n_rel, dtype="float32") / n_rel)          # -60 dB at the end of the release
            env[n_hold:] *= np.linspace(1.0, 0.0, n_rel, dtype="float32") ** 0.25                 # and to exactly zero, so nothing is cut
        gain = 10.0 ** (VEL_DB_PER_STEP * (vel - 64) / 20.0)
        return out * env[:, None] * np.float32(gain)

    @staticmethod
    def legato_flags(notes):
        """Which notes sit inside a slur (and are not its last note): per voice, in time order, 's' opens, 'e' closes, 'se' closes one and opens the next."""
        by_voice, flags = {}, [False] * len(notes)
        for i, nt in enumerate(notes):
            by_voice.setdefault(nt.get("voice", ""), []).append(i)
        for idxs in by_voice.values():
            inside = False
            for i in sorted(idxs, key=lambda j: (notes[j]["t"], notes[j]["pitch"])):
                sl = notes[i].get("sl", "")
                if sl in ("s", "se"):
                    inside, flags[i] = True, True
                elif sl == "e":
                    inside, flags[i] = False, False
                else:
                    flags[i] = inside
        return flags

    def render(self, notes, seconds):
        """notes: dicts with t, dur, pitch, vel and optional art ('s' staccato, 'a' arpeggiated), g (grace), sl, voice. Returns float32 (n, 2).
        Arpeggiated chords are rolled 18 ms per voice, low to high; notes inside a slur overlap the next by 30 ms; staccato notes sound 45 percent of their length (at most 140 ms)."""
        out = np.zeros((int(round(seconds * SR)) + 4 * SR, 2), dtype="float32")
        legato, rolls = self.legato_flags(notes), {}
        for i in sorted(range(len(notes)), key=lambda j: (notes[j]["t"], notes[j]["pitch"])):
            nt = notes[i]
            t = nt["t"]
            if "a" in nt.get("art", ""):
                k = rolls.get(round(nt["t"], 4), 0)
                rolls[round(nt["t"], 4)] = k + 1
                t += 0.018 * k
            stac = "s" in nt.get("art", "")
            if nt.get("g"):
                sounding = nt["dur"] + 0.02
            elif stac:
                sounding = min(0.45 * nt["dur"], 0.14)
            elif legato[i]:
                sounding = nt["dur"] + 0.03
            else:
                sounding = 0.94 * nt["dur"]
            audio = self.note(nt["pitch"], nt["vel"], max(sounding, 0.03), stac)
            i0 = int(round(t * SR))
            if i0 < 0:
                audio, i0 = audio[-i0:], 0
            out[i0:i0 + len(audio)] += audio[:len(out) - i0]
        return out[:int(round(seconds * SR))]
