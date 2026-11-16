"""Tests for tspan.py against the real score cards and the generated Ode world (build/worlds/ode.x3d, made by gen/world_ode.py; tests that need it skip without it)."""
import copy, json, math, os, struct, sys, tempfile, wave
from fractions import Fraction as Fr
import pytest

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "score")
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tspan as T

WORLD = {p: os.path.join(ROOT, "build", "worlds", p + ".x3d") for p in ("ode", "turca")}


def card(p):
    return json.load(open(os.path.join(ROOT, "score", p + ".score.json"), encoding="utf-8"))


@pytest.fixture(scope="module", params=["ode", "turca"])
def clk(request):
    return T.Clock(card(request.param))


def test_every_note_start_round_trips_through_seconds_quarters_bar_beat(clk):
    bad = []
    for n in clk.card["notes"]:
        s = T.selector(clk, q0=Fr(n["q"]), q1=Fr(n["q"]) + 1)
        ok = abs(s["t0"] - n["t"]) <= 1.5e-6 and (s["bar0"], s["beat0"]) == (n["bar"], round(float(n["beat"]), 4)) and not T.check(s, clk)
        if n.get("g"):
            ok = True               # a grace note sits before the beat of the note it decorates: its q is the decorated note's
        if not ok:
            bad.append((n["id"], s["t0"], n["t"], s["bar0"], s["beat0"], n["bar"], n["beat"]))
    assert not bad, bad[:5]


def test_a_selector_for_a_note_holds_that_note(clk):
    for n in clk.card["notes"][::97]:
        if n.get("g"):
            continue
        s = T.selector_of_notes(clk, [n["id"]])
        assert n["id"] in s["onsets"] and not T.check(s, clk)


def test_window_is_half_open_at_the_onset_and_leaves_grace_notes_out(clk):
    plain = [n for n in clk.card["notes"] if not n.get("g") and n["t"] >= 2.0]
    for n in plain[::211]:
        assert n["id"] not in T.selector(clk, t0=n["t"] - 1.0, t1=n["t"])["onsets"]      # a note that starts at t1 belongs to the next window
        assert n["id"] in T.selector(clk, t0=n["t"], t1=n["t"] + 1.0)["onsets"]          # and to the one that starts at its onset
    graces = [n for n in clk.card["notes"] if n.get("g")]
    for n in graces[::17]:
        s = T.selector(clk, t0=n["t"] - 0.5, t1=n["t"] + 0.5)
        assert n["id"] not in s["onsets"]                                                  # the Turca's 32nd grace notes are not onsets of the feature tracks
    assert (len(graces) > 0) == (clk.card["piece"] == "turca")


def test_damaged_selectors_go_red(clk):
    base = T.selector(clk, t0=20.0, t1=22.5)
    assert not T.check(base, clk) and base["onsets"]
    damages = {
        "t0 moved": lambda s: s.update(t0=s["t0"] + 1.0),
        "q1 moved": lambda s: s.update(q1=str(Fr(s["q1"]) + 1)),
        "bar0 moved": lambda s: s.update(bar0=s["bar0"] + 1),
        "beat1 moved": lambda s: s.update(beat1=s["beat1"] + 0.5),
        "k0 moved": lambda s: s.update(k0=s["k0"] + 1),
        "k1 moved": lambda s: s.update(k1=s["k1"] - 1),
        "onset dropped": lambda s: s["onsets"].pop(),
        "onset added": lambda s: s["onsets"].append(clk.notes[-1]["id"]),
        "reversed": lambda s: s.update(t0=s["t1"], t1=s["t0"]),
        "kind": lambda s: s.update(kind="tspan/0"),
    }
    for name, f in damages.items():
        s = copy.deepcopy(base)
        f(s)
        assert T.check(s, clk), name


def test_selector_needs_one_kind_of_window(clk):
    with pytest.raises(ValueError):
        T.selector(clk, t0=1, t1=2, q0=0, q1=1)
    with pytest.raises(ValueError):
        T.selector(clk, t0=2, t1=1)


# ---- against the generated Ode world -----------------------------------------------------------------------------------------------------------------
needs_world = pytest.mark.skipif(not os.path.exists(WORLD["ode"]), reason="build/worlds/ode.x3d not generated (python3 -I gen/world_ode.py)")


@needs_world
def test_belt_keys_are_beats_on_the_clock():
    """BeltPos has one key per beat (world_ode.belt_keys): key b is the time of quarter b on the card's tempo map, to the key's own rounding (7 places of a fraction of D)."""
    c = T.Clock(card("ode"))
    D, buses = T.bus_times(WORLD["ode"])
    times = buses["BeltPos"]
    n = int(c.card["checks"]["quarters_performed"])
    assert len(times) == n + 2                                     # beats 0..n, then the held end key at D
    worst = 0.0
    for b in range(n + 1):
        s = T.selector(c, q0=Fr(b), q1=Fr(b + 1))
        worst = max(worst, abs(times[b] - s["t0"]))
    assert worst < 2e-5, worst                                     # 0.5e-7 of D = 10.8 microseconds at worst
    assert abs(D - (c.card["checks"]["seconds"] + 9.0)) < 1e-3     # D is the card's seconds plus the Ode's 9 s ring-out (worldlib.TAILS)


def _act_value(c, ids_in_window, tk, keys_prev, keys_next):
    """Independent recomputation of one smoothed ActBus value from the evidence notes only (the formula is the docstring of world_ode.activity_keys)."""
    def raw(t):
        return min(1.0, sum(c.by_id[i]["vel"] / 127.0 for i in ids_in_window if t - 0.5 <= c.by_id[i]["t"] < t + 0.5) / 9.0)
    if keys_prev is None or keys_next is None:
        return raw(tk)
    return 0.25 * raw(keys_prev) + 0.5 * raw(tk) + 0.25 * raw(keys_next)


@needs_world
def test_actbus_values_follow_from_their_selector_alone():
    c = T.Clock(card("ode"))
    D, buses = T.bus_times(WORLD["ode"], snap=0.001)               # ActBus is keyed on whole seconds, so the read-back times are snapped to the millisecond
    raw = T.bus_times(WORLD["ode"])[1]["ActBus"]
    ts, vals = buses["ActBus"], T.bus_values(WORLD["ode"], "ActBus")
    assert max(abs(a - b) for a, b in zip(ts, raw)) < 1.2e-5          # the read-back rounding is below 12 microseconds
    assert len(ts) == len(vals) == 217
    good, naive_bad, shifted_bad, sizes = 0, 0, 0, []
    for i, t in enumerate(ts):
        ends = i in (0, len(ts) - 1)
        lo = t - 0.5 if ends else ts[i - 1] - 0.5                  # the value reads the raw windows of its neighbours too (3-tap smoothing): its lineage is wider than +-0.5 s
        hi = t + 0.5 if ends else ts[i + 1] + 0.5
        s = T.selector(c, t0=max(lo, 0.0), t1=hi)
        assert not T.check(s, c)
        prev, nxt = (None, None) if ends else (ts[i - 1], ts[i + 1])
        v = _act_value(c, s["onsets"], t, prev, nxt)
        good += abs(v - vals[i]) <= 5.1e-4                         # keyValue is written to 3 places
        sizes.append(len(s["onsets"]))
        # the same key with only the +-0.5 s window around it: not enough evidence once the smoothing reads its neighbours
        s2 = T.selector(c, t0=max(t - 0.5, 0.0), t1=t + 0.5)
        v2 = _act_value(c, s2["onsets"], t, prev, nxt)
        naive_bad += abs(v2 - vals[i]) > 5.1e-4
        # and a window slid by one second
        s3 = T.selector(c, t0=max(lo + 1.0, 0.0), t1=hi + 1.0)
        v3 = _act_value(c, s3["onsets"], t, prev, nxt)
        shifted_bad += abs(v3 - vals[i]) > 5.1e-4
    print("ActBus: %d of %d keys recomputed from their selector's onsets alone; the +-0.5 s window alone fails %d; a window slid by 1 s fails %d; evidence per key %d..%d notes" %
          (good, len(ts), naive_bad, shifted_bad, min(sizes), max(sizes)))
    assert good == len(ts)
    assert naive_bad > 20 and shifted_bad > 20                   # the check is not vacuous


@needs_world
def test_window_to_keys_and_back():
    c = T.Clock(card("ode"))
    D, buses = T.bus_times(WORLD["ode"])
    s = T.selector(c, q0=Fr(36), q1=Fr(40))                       # bars 10 (4/4): one bar of the Ode
    assert (s["bar0"], s["beat0"], s["bar1"], s["beat1"]) == (10, 1.0, 11, 1.0)
    idx = T.keys_in_window(buses["ActBus"], s["t0"], s["t1"])
    assert idx and all(s["t0"] - 2e-5 <= buses["ActBus"][i] < s["t1"] for i in idx) and len(idx) in (2, 3)
    beats = T.keys_in_window(buses["BeltPos"], s["t0"], s["t1"])
    assert beats == [36, 37, 38, 39]                              # four beats, four belt keys


# ---- the audio branch, on a synthetic master ---------------------------------------------------------------------------------------------------------
def _tone_wav(path, sr=48000, dur=4.0, on=(1.0, 2.0), amp=0.5, hz=1000.0):
    n = int(sr * dur)
    xs = [int(32767 * amp * math.sin(2 * math.pi * hz * k / sr)) if on[0] <= k / sr < on[1] else 0 for k in range(n)]
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(struct.pack("<%dh" % n, *xs))


def test_audio_window_recomputes_a_loudness_claim():
    c = T.Clock(card("ode"))
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "click.wav")
        _tone_wav(p)
        s_on = T.selector(c, t0=1.25, t1=1.75, audio={"sr": 48000, "sha256": "0" * 64})
        s_off = T.selector(c, t0=2.5, t1=3.0, audio={"sr": 48000, "sha256": "0" * 64})
        assert not T.check(s_on, c) and (s_on["audio"]["s0"], s_on["audio"]["s1"]) == (60000, 84000)
        on, off = T.rms_dbfs_wav(p, s_on["audio"]["s0"], s_on["audio"]["s1"]), T.rms_dbfs_wav(p, s_off["audio"]["s0"], s_off["audio"]["s1"])
        assert abs(on - (-9.03)) < 0.05 and off == float("-inf")        # 0.5 / sqrt(2) = -9.03 dBFS; silence outside the tone
        bad = copy.deepcopy(s_on)
        bad["audio"]["s0"] += 1
        assert T.check(bad, c)
