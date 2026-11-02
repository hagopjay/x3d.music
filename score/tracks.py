#!/usr/bin/env python3
"""Feature tracks at 60 Hz from a score card (schema loomsong.tracks/1). Stdlib only.

Every channel here is Exact in the spec's sense: it is computed from the card alone (no audio is read). Samples sit at t = k / 60 s, k = 0 .. n - 1. A note counts as sounding from its
`t` for its `dur` (the notated length; staccato and pedal are the renderer's business). Channels are stored as little-endian int16 in base64, uncompressed, so the file's bytes do not
depend on the zlib version that made it. The page parts (gzip plus base64 text of at most 9 MB, decoded with DecompressionStream) are made from these by page_part() when the page is built.

  beat_phase  position inside the quarter-note beat, 0 to 1 (x1000)
  bar_phase   position inside the bar, 0 to 1 (x1000), the upbeat counted as the end of bar 0
  section     index of the form pass (card.form) the time falls in
  harmony     index of the harmony segment (card.harmony) the time falls in
  tension     spiral-array tension of that segment (x1000)
  density     composer note onsets per second in a 1 s window centred on t, grace notes not counted (x10)
  contour     MIDI pitch of the highest sounding composer note; the last value is held through rests
  lo, hi      lowest and highest sounding pitch, held through rests
  active      number of composer notes sounding
"""
import base64, bisect, gzip, json, math, os, struct, sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cardlib import TempoMap, sha256_file   # noqa: E402

FS = 60
CHANNELS = {"beat_phase": 1000, "bar_phase": 1000, "section": 1, "harmony": 1, "tension": 1000, "density": 10, "contour": 1, "lo": 1, "hi": 1, "active": 1}


def tempo_map(card):
    return TempoMap([(Fr(e["q"]), Fr(e["qpm"])) for e in card["tempo_map"]])


def pickup_of(card):
    """Quarters of upbeat before the first full bar (0 when the first bar is full)."""
    beats = int(card["meter"].split("/")[0])
    first = card["tempo_map"][0]
    return (beats - (int(first["beat"]) - 1)) % beats if first["bar"] == 0 else 0


def sounding(card):
    return sorted(((n["t"], n["t"] + n["dur"], n["pitch"] + 12 * n.get("oct", 0), n.get("g", 0)) for n in card["notes"] if n["layer"] == "composer"))


def compute(card):
    """Return {channel: [int]} for the card, plus n."""
    tm = tempo_map(card)
    beats = int(card["meter"].split("/")[0])
    pickup = pickup_of(card)
    T = card["checks"]["seconds"]
    n = int(math.ceil(T * FS)) + 1
    ev = sounding(card)
    onsets = sorted(t for t, _, _, g in ev if not g)
    form_q = [(Fr(f["q0"]), Fr(f["q1"])) for f in card["form"]]
    harm_t = [h["t"] for h in card["harmony"]]
    out = {k: [] for k in CHANNELS}
    active, i = [], 0
    held = {"contour": 0, "lo": 0, "hi": 0}
    for k in range(n):
        t = k / FS
        q = tm.quarters(Fr(k, FS))
        x = q + (beats - pickup) if pickup else q
        bp = float(q % 1)
        out["beat_phase"].append(int(round(bp * 1000)) % 1000)
        out["bar_phase"].append(int(round(float((x % beats) / beats) * 1000)) % 1000)
        sec = next((j for j, (a, b) in enumerate(form_q) if a <= q < b), len(form_q) - 1)
        out["section"].append(sec)
        h = max(0, bisect.bisect_right(harm_t, t + 1e-9) - 1)
        out["harmony"].append(h)
        out["tension"].append(int(round(card["harmony"][h]["tension"] * 1000)))
        out["density"].append(int(round((bisect.bisect_left(onsets, t + 0.5) - bisect.bisect_left(onsets, t - 0.5)) * 10)))
        while i < len(ev) and ev[i][0] <= t + 1e-9:
            active.append(ev[i])
            i += 1
        active = [a for a in active if a[1] > t + 1e-9]
        if active:
            ps = [a[2] for a in active]
            held = {"contour": max(ps), "lo": min(ps), "hi": max(ps)}
        out["contour"].append(held["contour"])
        out["lo"].append(held["lo"])
        out["hi"].append(held["hi"])
        out["active"].append(len(active))
    return out, n


def pack(values):
    return base64.b64encode(struct.pack("<%dh" % len(values), *values)).decode("ascii")


def unpack(b64, n):
    return list(struct.unpack("<%dh" % n, base64.b64decode(b64)))


def page_part(values):
    """The shape the page decodes with DecompressionStream: gzip (mtime 0) of the int16 bytes, in base64."""
    return base64.b64encode(gzip.compress(struct.pack("<%dh" % len(values), *values), 9, mtime=0)).decode("ascii")


def build(card, card_path):
    ch, n = compute(card)
    return {"schema": "loomsong.tracks/1", "piece": card["piece"], "licence": card["licence"], "fs": FS, "n": n, "card": os.path.basename(card_path), "card_sha256": sha256_file(card_path),
            "note": "t = k / fs seconds. A note sounds from t for dur. Each channel is int16 little-endian in base64; divide by scale.",
            "channels": {k: {"dtype": "i16le", "scale": CHANNELS[k], "b64": pack(v)} for k, v in ch.items()}}


def write(obj, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        keys = list(obj.keys())
        for i, k in enumerate(keys):
            c = "," if i < len(keys) - 1 else ""
            if k == "channels":
                f.write(' "channels": {\n')
                items = list(obj[k].items())
                for j, (name, v) in enumerate(items):
                    f.write('  "%s": %s%s\n' % (name, json.dumps(v, separators=(",", ":")), "," if j < len(items) - 1 else ""))
                f.write(" }%s\n" % c)
            else:
                f.write(' "%s": %s%s\n' % (k, json.dumps(obj[k], ensure_ascii=False, separators=(",", ":")), c))
        f.write("}\n")
