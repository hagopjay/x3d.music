"""Mix and master: each stem normalised, shaped by its own chain, ducked by the kick where the recipe says so, balanced left to right and sent to the spaces; the drums glued on a bus; the snare and
clap in a gated plate; a gentle master chain; then loudness to -14 LUFS with the true peak under -1 dBTP.

Everything here is arithmetic on arrays and pedalboard's built-in effects, so a rerun on one machine gives the same samples. The recipes (recipes.py) say what each piece wants; this file is the machinery.
Conventions: audio is float32 shaped (n, 2); a stem's `level` is its integrated loudness in LUFS after its chain, at its fader, before ducking and panning; every send level is in dB relative to the stem at the fader; every return is trimmed so that 0 dB means the space returns as much level as it was sent
(SPACE_TRIM_DB, measured by calibrate_spaces()).
"""
import numpy as np
from pedalboard import Delay, HighpassFilter, LowpassFilter, Pedalboard, Reverb
from scipy import ndimage, signal

import meter

SR = meter.SR
REF_DB = -23.0              # every stem is brought to this RMS (of its playing blocks) first, so the dynamics processors in its chain see the same level whatever the synth patch put out
SPACES = ("hall", "room", "plate", "delay")


def run(board, x):
    """Apply a pedalboard to float32 audio shaped (n, 2)."""
    y = board(np.ascontiguousarray(x.T, dtype="float32"), SR)
    return np.ascontiguousarray(y.T)


def db(x):
    return np.float32(10 ** (x / 20))


def normalise(x, ref=REF_DB):
    if not np.abs(x).max() > 1e-6:
        return x
    return x * db(ref - meter.active_rms_db(x))


def balance(x, pan):
    """A balance control: pan in [-1, 1]; the far channel falls, the near one stays."""
    return x * np.array([min(1.0, 1.0 - pan), min(1.0, 1.0 + pan)], dtype="float32")


def duck_curve(n, times, depth, tau=0.12, span=0.6):
    """Gain over time that dips by `depth` (0.3 is about -3 dB) at every time in `times` and recovers with time constant tau (seconds)."""
    g = np.ones(n, dtype="float32")
    m = int(span * SR)
    shape = (1.0 - depth * np.exp(-np.arange(m) / (tau * SR))).astype("float32")
    for t in times:
        i = int(round(t * SR))
        if 0 <= i < n:
            j = min(n, i + m)
            g[i:j] = np.minimum(g[i:j], shape[:j - i])
    return g


def gate_curve(n, times, hold=0.17, fade=0.045):
    """A gate that opens on every time in `times`, holds, and closes in `fade` seconds: the gated plate."""
    g = np.zeros(n, dtype="float32")
    h, f = int(hold * SR), int(fade * SR)
    shape = np.concatenate([np.ones(h, dtype="float32"), np.linspace(1.0, 0.0, f, dtype="float32")])
    for t in times:
        i = int(round(t * SR))
        if 0 <= i < n:
            j = min(n, i + len(shape))
            g[i:j] = np.maximum(g[i:j], shape[:j - i])
    return g


def predelay(x, seconds):
    k = int(seconds * SR)
    return np.concatenate([np.zeros((k, 2), dtype="float32"), x[:len(x) - k]]) if k else x


def spaces(spq):
    """The reverbs and the delay: a hall, a short room, a big plate (gated afterwards), a dotted-eighth stereo delay. Wet only."""
    return {
        "hall": Pedalboard([Reverb(room_size=0.84, damping=0.42, wet_level=1.0, dry_level=0.0, width=1.0), HighpassFilter(180), LowpassFilter(9500)]),
        "room": Pedalboard([Reverb(room_size=0.28, damping=0.6, wet_level=1.0, dry_level=0.0, width=0.9), HighpassFilter(200)]),
        "plate": Pedalboard([Reverb(room_size=0.93, damping=0.3, wet_level=1.0, dry_level=0.0, width=1.0), HighpassFilter(250)]),
        "delay": Pedalboard([Delay(delay_seconds=0.75 * spq, feedback=0.32, mix=1.0), HighpassFilter(300), LowpassFilter(6500)]),
    }


# Measured by calibrate_spaces(): the dB to add so that a space returns, on band-limited noise, as much level (RMS) as went in.
SPACE_TRIM_DB = {"hall": -6.76, "room": -2.6, "plate": -9.12, "delay": 1.23}


def calibrate_spaces(seconds=20.0, qpm=126.0, seed=7):
    """RMS of each space's output over its input, on pink-ish noise, in dB. The numbers go into SPACE_TRIM_DB (negated)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    x = rng.standard_normal((n, 2)).astype("float32")
    x = run(Pedalboard([LowpassFilter(4000), HighpassFilter(150)]), x) * np.float32(0.1)
    out = {}
    for k, b in spaces(60.0 / qpm).items():
        y = run(b, x)
        out[k] = round(float(20 * np.log10(np.sqrt((y[SR:] ** 2).mean()) / np.sqrt((x[SR:] ** 2).mean()))), 2)
    return out


def ride(x, form, arc, ramp=0.5, shortest=2.0):
    """Fader rides: bring every pass of the form to the loudness the recipe's arc asks of it (LUFS of that pass, relative to the others; the master sets the absolute level afterwards).
    Passes shorter than `shortest` seconds (the first and second endings) keep the ride of the pass before them; the steps between passes are smoothed over `ramp` seconds.
    Returns (audio, {pass: ride in dB})."""
    rides, last = {}, 0.0
    curve = np.zeros(len(x))
    for f in form:
        key = "%s%d" % (f["id"], f["rep"])
        i0, i1 = int(round(f["t0"] * SR)), min(len(x), int(round(f["t1"] * SR)))
        if f["t1"] - f["t0"] >= shortest and key in arc:
            last = arc[key] - meter.lufs(x[i0:i1])
        rides[key] = round(float(last), 2)
        curve[i0:i1] = last
    curve[int(round(form[-1]["t1"] * SR)):] = last                    # the ring-out after the last note keeps the last ride
    curve = ndimage.uniform_filter1d(curve, size=max(1, int(ramp * SR)), mode="nearest")
    return (x * (10 ** (curve / 20))[:, None].astype("float32")).astype("float32"), rides


_JOB = {}


def _prepare_stem(inst):
    """One stem up to its fader: normalised, through its chain, set to its level, its peaks held to `crest` dB over that level, trimmed. Independent of every other stem, so it runs in a worker."""
    r = _JOB["recipe"]["stems"][inst]
    y = run(r["chain"](), normalise(_JOB["stems"][inst]))
    if np.abs(y).max() > 1e-6:
        if "level" in r:
            y = y * db(r["level"] - meter.lufs(y))             # the recipe names the loudness the stem has at its fader, whatever the chain did to its level
        if "crest" in r:
            y, _ = limit(y, r["level"] + r["crest"], lookahead_ms=1.0, release_ms=40.0)   # no peak more than `crest` dB over that loudness: hats and cymbals arrive 30 dB over theirs
    return inst, y * db(r.get("gain", 0.0))


def mix(stems, card, recipe, workers=4):
    """stems: {instrument id: float32 (n, 2)}; card: the score card (for the kick, snare and clap times); recipe: see recipes.py.
    Returns the float32 (n, 2) sum before mastering and {"faded": {instrument: its stem after chain, fader, ducking and pan}, "returns": {space: what the space adds}, "report": {...}, "rides_db": {...}}."""
    n = len(next(iter(stems.values())))
    spq = 60.0 / (recipe.get("qpm") or card["perform"]["qpm"])
    hits = {i: [x["t"] for x in card["notes"] if x["inst"] == i] for i in ("kick", "snare", "clap", "rim")}
    drums = np.zeros((n, 2), dtype="float32")
    music = np.zeros((n, 2), dtype="float32")
    send_in = {k: np.zeros((n, 2), dtype="float32") for k in SPACES}
    report, faded, returned = {}, {}, {}
    _JOB.update(stems=stems, recipe=recipe)
    names = sorted(stems)
    if workers > 1:
        import multiprocessing
        with multiprocessing.get_context("fork").Pool(min(workers, len(names))) as pool:
            prepared = dict(pool.map(_prepare_stem, names, chunksize=1))
    else:
        prepared = dict(_prepare_stem(i) for i in names)
    for inst in names:
        r = recipe["stems"][inst]
        y = prepared.pop(inst)
        if r.get("duck"):
            y = y * duck_curve(n, hits["kick"], r["duck"])[:, None]
        y = balance(y, r.get("pan", 0.0))
        for space, level in r.get("sends", {}).items():
            send_in[space] += y * db(level)
        faded[inst] = y
        if r.get("bus") == "drums":
            drums += y
        else:
            music += y
        report[inst] = {"level_lufs": r.get("level"), "peak_dbfs": round(meter.sample_peak_db(y), 1)}
    drums = run(recipe["drum_bus"](), drums)
    sp = spaces(spq)
    total = drums + music
    for space in SPACES:
        s = send_in[space]
        if not np.abs(s).max() > 1e-9:
            continue
        if space == "plate":
            s = run(sp[space], predelay(s, 0.012)) * gate_curve(n, hits["snare"] + hits["clap"] + hits["rim"])[:, None]
        elif space == "delay":
            s = run(sp[space], s)
        else:
            s = run(sp[space], predelay(s, 0.02))
        returned[space] = s * db(recipe["returns"].get(space, 0.0) + SPACE_TRIM_DB[space])
        total = total + returned[space]
    rides = None
    if recipe.get("arc"):
        total, rides = ride(total, card["form"], recipe["arc"])
    return total, {"faded": faded, "returns": returned, "report": report, "rides_db": rides}


def leaky_max(a, d):
    """e[n] = max over k >= 0 of a[n-k] * d**k, for a >= 0: an envelope that jumps up with `a` and decays by the factor d per sample. Vectorised in blocks (a running maximum of a * d**-j)."""
    n = len(a)
    block = max(64, int(5.0 / -np.log(d)))
    j = np.arange(block)
    dpow, dinv = d ** j, d ** -j.astype("float64")
    out = np.empty_like(a)
    carry = 0.0
    for i in range(0, n, block):
        seg = a[i:i + block]
        m = len(seg)
        acc = np.maximum(np.maximum.accumulate(seg * dinv[:m]), carry * d)
        out[i:i + m] = acc * dpow[:m]
        carry = out[i + m - 1]
    return out


def true_peak_envelope(x, floor, context=32):
    """Per frame, the largest 4x-oversampled magnitude over both channels (what the true-peak meter reads), but only measured where the signal gets within 6 dB of the ceiling it will be limited
    to: frames whose neighbourhood never exceeds `floor` keep their sample peak, which no inter-sample overshoot of music takes from under `floor` to the ceiling. Oversampling every frame costs
    seconds a stem; the loud frames are a few percent."""
    a = np.maximum(np.abs(x[:, 0]), np.abs(x[:, 1])).astype("float64")
    hot = ndimage.maximum_filter1d((a > floor).astype("uint8"), size=2 * context + 1)
    idx = np.flatnonzero(hot)
    if not len(idx):
        return a
    cut = np.flatnonzero(np.diff(idx) > 1)
    starts, ends = idx[np.r_[0, cut + 1]], idx[np.r_[cut, len(idx) - 1]] + 1
    peak = a.copy()
    for lo, hi in zip(starts, ends):
        c0 = max(0, lo - context)
        over = np.abs(signal.resample_poly(x[c0:hi + context].astype("float32"), 4, 1, axis=0, padtype="line"))
        seg = over[4 * (lo - c0):4 * (hi - c0)]
        peak[lo:hi] = np.maximum(a[lo:hi], np.maximum(seg[:, 0], seg[:, 1]).reshape(-1, 4).max(axis=1))
    return peak


def limit(x, ceiling_db=-1.2, lookahead_ms=2.0, release_ms=70.0):
    """A transparent offline limiter: no latency, no overshoot. The true peak of every sample (4x oversampled, as the meter measures it) sets the gain it needs; a sliding minimum over +-lookahead
    followed by a triangular smoothing of the same support keeps the gain at or under that need everywhere while turning down before the peak and not after; then a release that decays with
    time constant release_ms. Returns (audio, gain curve)."""
    ceil = 10 ** (ceiling_db / 20)
    peak = true_peak_envelope(x, 0.5 * ceil)
    need = np.minimum(1.0, ceil / np.maximum(peak, 1e-9))
    if need.min() >= 1.0:
        return x, np.ones(len(x))
    half = int(round(lookahead_ms * 1e-3 * SR))
    size = 2 * (half // 2) + 1                                          # odd; two boxes of this size have a total support of 2*size - 1 <= 2*half + 1
    low = ndimage.minimum_filter1d(need, size=2 * half + 1, mode="nearest")
    smooth = ndimage.uniform_filter1d(ndimage.uniform_filter1d(low, size=size, mode="nearest"), size=size, mode="nearest")
    gain = 1.0 - leaky_max(1.0 - smooth, float(np.exp(-1.0 / (release_ms * 1e-3 * SR))))
    return (x * gain[:, None].astype("float32")).astype("float32"), gain


def master(x, recipe, target=-14.0, ceiling=-1.5):
    """The master chain, then gain and the limiter until the integrated loudness lands on `target` with the true peak at or under `ceiling` dBTP. Returns (audio, report)."""
    y = run(recipe["master_chain"](), x)
    gain = target - meter.lufs(y)
    out, g = y, np.ones(len(y))
    for _ in range(12):
        out, g = limit(y * db(gain), ceiling)
        err = target - meter.lufs(out)
        if abs(err) < 0.02:
            break
        gain += err
    red = -20 * np.log10(np.maximum(g, 1e-6))
    return out, {"gain_into_limiter_db": round(float(gain), 2), "max_reduction_db": round(float(red.max()), 2), "mean_reduction_db": round(float(red.mean()), 3),
                 "seconds_over_1db_reduction": round(float((red > 1.0).sum() / SR), 2)}
