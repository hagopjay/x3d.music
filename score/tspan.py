"""tspan: time-span selectors for audio-driven visuals (the LOCATE step for music). Stdlib only.

A score card is the single source of truth (docs/SCORE-SCHEMA.md), so a driver value in a Loomsong world (an interpolator key, a 60 Hz track sample, a texel) comes
from a window of the performance clock and from the notes inside it. The article's limit "a quote is not mapped to a time in the recording" is closed by a selector:

    {"kind": "tspan/1", "clock": "performance",
     "t0": 57.0, "t1": 58.0,                  seconds on the performance clock (t = 0 is sample 0 of the master), half-open [t0, t1), six decimals like the card
     "q0": "104", "q1": "105",               the same window in exact quarters (strings, like the card); bar0/beat0/bar1/beat1 on the performed grid
     "fs": 60, "k0": 3420, "k1": 3480,       frames of the 60 Hz tracks: k0 <= k < k1  <=>  t0 <= k / 60 < t1
     "onsets": ["ode.S2.mel.M.0031", ...],   ids of the card's notes whose onset lies in the window (grace notes excluded): the evidence, the analogue of the quote
     "audio": {"sr": 48000, "s0": 2736000, "s1": 2784000, "sha256": "..."}   optional: the same window in samples of a rendered master, pinned by hash
    }

`check(selector, clock)` re-derives every field from the card and says what differs; a feature value can then be recomputed from the evidence alone (test_tspan.py).
`bus_times` / `keys_in_window` map a window to the keys of an interpolator in a generated X3D (key fraction x D = seconds, D from SecondsBus).
"""
import bisect, math, struct, wave
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cardlib import TempoMap, metric      # noqa: E402  (the repository's own exact tempo map and bar/beat arithmetic)

KIND = "tspan/1"
FS = 60


class Clock:
    """The card as a clock: seconds <-> exact quarters <-> performed bar and beat, plus the notes by onset."""

    def __init__(self, card):
        self.card = card
        self.tm = TempoMap([(Fr(e["q"]), Fr(e["qpm"])) for e in card["tempo_map"]])
        beats = self.beats = int(card["meter"].split("/")[0])
        first = card["tempo_map"][0]
        self.pickup = (beats - (int(first["beat"]) - 1)) % beats if first["bar"] == 0 else 0
        self.notes = sorted(card["notes"], key=lambda n: (n["t"], n["id"]))
        self._ts = [n["t"] for n in self.notes]
        self.by_id = {n["id"]: n for n in self.notes}

    def t_of_q(self, q):
        return round(float(self.tm.seconds(Fr(q))), 6)

    def q_of_t(self, t):
        return self.tm.quarters(Fr(t).limit_denominator(10 ** 7))

    def onsets(self, t0, t1, graces=False):
        i, j = bisect.bisect_left(self._ts, t0), bisect.bisect_left(self._ts, t1)
        return [n["id"] for n in self.notes[i:j] if graces or not n.get("g")]


def _frac(q):
    q = Fr(q)
    return str(q.numerator) if q.denominator == 1 else "%d/%d" % (q.numerator, q.denominator)


def selector(clock, t0=None, t1=None, q0=None, q1=None, audio=None):
    """A selector for a window given in seconds or in quarters (exactly one of the two pairs). `audio` = {"sr":, "sha256":} adds the sample window."""
    if (t0 is None) == (q0 is None):
        raise ValueError("give seconds (t0, t1) or quarters (q0, q1), not both")
    if q0 is not None:
        q0, q1 = Fr(q0), Fr(q1)
        t0, t1 = clock.t_of_q(q0), clock.t_of_q(q1)
    else:
        t0, t1 = round(float(t0), 6), round(float(t1), 6)
        q0, q1 = clock.q_of_t(t0), clock.q_of_t(t1)
    if not t1 > t0:
        raise ValueError("an empty or reversed window")
    b0, e0 = metric(q0, clock.pickup, clock.beats)
    b1, e1 = metric(q1, clock.pickup, clock.beats)
    sel = dict(kind=KIND, clock="performance", t0=t0, t1=t1, q0=_frac(q0), q1=_frac(q1), bar0=b0, beat0=round(float(e0), 4), bar1=b1, beat1=round(float(e1), 4),
               fs=FS, k0=math.ceil(t0 * FS - 1e-9), k1=math.ceil(t1 * FS - 1e-9), onsets=clock.onsets(t0, t1))
    if audio:
        sel["audio"] = dict(sr=audio["sr"], s0=round(t0 * audio["sr"]), s1=round(t1 * audio["sr"]), sha256=audio["sha256"])
    return sel


def selector_of_notes(clock, ids):
    """The smallest window that holds the whole of each named note (onset to onset + dur)."""
    ns = [clock.by_id[i] for i in ids]
    return selector(clock, t0=min(n["t"] for n in ns), t1=max(n["t"] + n["dur"] for n in ns))


def check(sel, clock):
    """Every field of a selector re-derived from the card. Returns a list of problems; empty means verified."""
    bad = []
    if sel.get("kind") != KIND:
        return ["kind"]
    t0, t1 = sel["t0"], sel["t1"]
    if not t1 > t0:
        bad.append("window empty or reversed")
    if t0 < 0 or t1 > clock.card["checks"]["seconds"] + 60:
        bad.append("window outside the piece")
    for name, t in (("q0", t0), ("q1", t1)):
        if abs(clock.t_of_q(Fr(sel[name])) - t) > 5e-7:
            bad.append("%s does not give t on the tempo map" % name)
    for b, e, q in (("bar0", "beat0", sel["q0"]), ("bar1", "beat1", sel["q1"])):
        mb, me = metric(Fr(q), clock.pickup, clock.beats)
        if (sel[b], sel[e]) != (mb, round(float(me), 4)):
            bad.append("%s/%s are not the performed bar and beat of %s" % (b, e, q))
    if (sel["k0"], sel["k1"]) != (math.ceil(t0 * sel["fs"] - 1e-9), math.ceil(t1 * sel["fs"] - 1e-9)):
        bad.append("k0/k1 are not the 60 Hz frames of the window")
    if sel["onsets"] != clock.onsets(t0, t1):
        bad.append("onsets differ from the card's notes in the window")
    a = sel.get("audio")
    if a and (a["s0"], a["s1"]) != (round(t0 * a["sr"]), round(t1 * a["sr"])):
        bad.append("s0/s1 are not the samples of the window")
    return bad


# ---- the X3D side: key fraction x D = seconds ----------------------------------------------------------------------------------------------------
def _floats(s):
    return [float(x) for x in s.replace(",", " ").split()]


def bus_times(x3d_path, snap=None):
    """(D, {DEF: [seconds of each key]}) for every *Interpolator in a generated world; D is the last keyValue of SecondsBus (worldlib.time_bus).
    Keys are written as fractions of D to 7 places, so a time read back is good to about 11 microseconds (half of D / 1e7) and a note whose onset sits on a window edge can fall either side:
    pass `snap` (for example 0.001, for a bus keyed on whole seconds) to round the times to the grid the bus was built on."""
    root = ET.parse(x3d_path).getroot()
    nodes = {e.get("DEF"): e for e in root.iter() if e.get("DEF") and e.tag.endswith("Interpolator")}
    D = _floats(nodes["SecondsBus"].get("keyValue"))[-1]
    q = (lambda t: round(round(t / snap) * snap, 9)) if snap else (lambda t: round(t, 6))
    return D, {d: [q(k * D) for k in _floats(e.get("key"))] for d, e in nodes.items() if d not in ("FractionBus", "SecondsBus")}


def bus_values(x3d_path, def_name):
    e = [e for e in ET.parse(x3d_path).getroot().iter() if e.get("DEF") == def_name][0]
    return _floats(e.get("keyValue"))


def keys_in_window(times, t0, t1, eps=2e-5):
    """Indices of the keys whose time lies in [t0, t1), give or take eps (the key rounding above, 2e-5 s = 1/833 of a frame at 60 Hz): which part of a bus a window drives."""
    return [i for i, t in enumerate(times) if t0 - eps <= t < t1 - eps]


# ---- the audio side: a window of a rendered master (16-bit PCM WAV; the real masters are FLAC and need soundfile) --------------------------------------------
def rms_dbfs_wav(path, s0, s1):
    with wave.open(path, "rb") as w:
        assert w.getsampwidth() == 2, "16-bit PCM only in this prototype"
        ch = w.getnchannels()
        w.setpos(s0)
        raw = w.readframes(s1 - s0)
    xs = struct.unpack("<%dh" % (len(raw) // 2), raw)
    if not xs:
        return float("-inf")
    ms = sum((x / 32768.0) ** 2 for x in xs) / len(xs)
    return 10 * math.log10(ms) if ms > 0 else float("-inf")
