#!/usr/bin/env python3
"""Render a piece's audio: stems from the score card, the mix, the master, and the measurements.

    python3 audio/render.py turca|ode|all [--out build/audio] [--fresh] [--tail SECONDS]

Writes  <out>/<piece>/raw/<inst>.wav (float32 stems straight from the instruments, cached), <out>/<piece>/stems/<inst>.wav (24-bit, post chain and fader, one common gain, none clipped),
<out>/<piece>/<piece>.master.wav (48 kHz, 24-bit) and <out>/<piece>/report.json. Nothing here is committed: the audio is rebuilt from the cards.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import meter, mix, rack, recipes  # noqa: E402


def newest(paths):
    return max(os.path.getmtime(p) for p in paths)


def load_or_render(card, card_path, seconds, raw_dir, fresh):
    """Stems from cache when they are newer than everything that makes them: the card, the rack, the shared Faust library, that instrument's own voice file (the sampler for the piano)."""
    os.makedirs(raw_dir, exist_ok=True)
    by = rack.instrument_notes(card)
    stems, todo = {}, []
    for inst in sorted(by):
        path = os.path.join(raw_dir, inst + ".wav")
        own = [os.path.join(HERE, "sampler.py")] if inst == "pno" else [os.path.join(rack.FAUST, rack.RACK[inst]["dsp"]), os.path.join(rack.FAUST, "common.lib")]
        deps = newest([card_path, rack.__file__] + own)
        if not fresh and os.path.exists(path) and os.path.getmtime(path) > deps and sf.info(path).frames == int(round(seconds * rack.SR)):
            stems[inst] = sf.read(path, dtype="float32")[0]
        else:
            todo.append(inst)
    grand = None
    for inst in todo:
        t0 = time.time()
        if inst == "pno":
            from sampler import Grand
            grand = grand or Grand()
            one = rack.render_stems({**card, "notes": [n for n in card["notes"] if n["inst"] == "pno"]}, seconds, grand)["pno"]
        else:
            one = rack.render_faust(inst, by[inst], seconds)
        sf.write(os.path.join(raw_dir, inst + ".wav"), one, rack.SR, subtype="FLOAT")
        stems[inst] = one
        print("  rendered %-9s %5.1f s" % (inst, time.time() - t0), flush=True)
    return stems


def export_stems(info, folder):
    """The stems as 24-bit WAV: after chain, fader, ducking and pan, before the bus, the spaces and the master; the spaces' returns as stems of their own. One common gain for all, so that the
    loudest stem peaks at -1 dBFS and none clips; the balance between stems is the mix's."""
    os.makedirs(folder, exist_ok=True)
    every = {**info["faded"], **{"fx_" + k: v for k, v in info["returns"].items()}}
    peak = max(float(np.abs(v).max()) for v in every.values())
    k = min(1.0, 10 ** (-1.0 / 20) / peak) if peak > 0 else 1.0
    for inst, v in every.items():
        sf.write(os.path.join(folder, inst + ".wav"), (v * np.float32(k)).astype("float32"), rack.SR, subtype="PCM_24")
    return {"common_gain_db": round(float(20 * np.log10(k)), 2), "stems": sorted(every)}


TAILS = {"turca": 6.0, "ode": 9.0}          # seconds of ring-out after the last note; the Ode's coda is a ritardando into one big hit and its hall needs longer to die away


def render(piece, out_root, fresh=False, tail=None):
    """Render one piece end to end; returns the report that is also written to <out_root>/<piece>/report.json."""
    card_path = os.path.join(ROOT, "score", piece + ".score.json")
    card = json.load(open(card_path))
    seconds = card["checks"]["seconds"] + (TAILS[piece] if tail is None else tail)
    out = os.path.join(out_root, piece)
    t0 = time.time()
    stems = load_or_render(card, card_path, seconds, os.path.join(out, "raw"), fresh)
    print("%s: stems ready in %.1f s" % (piece, time.time() - t0), flush=True)
    recipe = recipes.RECIPES[piece]
    t1 = time.time()
    premaster, info = mix.mix(stems, card, recipe)
    in_mix = info["report"]
    final, master_report = mix.master(premaster, recipe)
    print("%s: mixed and mastered in %.1f s" % (piece, time.time() - t1), flush=True)
    export_stems(info, os.path.join(out, "stems"))
    m = os.path.join(out, piece + ".master.wav")
    sf.write(m, final, rack.SR, subtype="PCM_24")
    report = {"piece": piece, "seconds": round(len(final) / rack.SR, 3), "lufs": round(meter.lufs(final), 2), "true_peak_dbtp": round(meter.true_peak_db(final), 2),
              "sample_peak_dbfs": round(meter.sample_peak_db(final), 2), "stereo_correlation": round(meter.stereo_correlation(final), 3), "bands_db": meter.band_levels(final),
              "ebur128": meter.ebur128(m), "stems_in_mix": in_mix, "rides_db": info["rides_db"], "master": master_report}
    json.dump(report, open(os.path.join(out, "report.json"), "w"), indent=1)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("piece", choices=sorted(TAILS) + ["all"])
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "audio"))
    ap.add_argument("--fresh", action="store_true", help="render the stems again even if cached")
    ap.add_argument("--tail", type=float, default=None, help="seconds of ring-out after the last note (default: %s)" % TAILS)
    a = ap.parse_args()
    for piece in (sorted(TAILS) if a.piece == "all" else [a.piece]):
        r = render(piece, a.out, a.fresh, a.tail)
        print("%s: %.3f s, %.2f LUFS, %.2f dBTP (own), loudness range %.1f LU (ffmpeg %.1f LUFS, %.1f dBTP), correlation %.3f" % (piece, r["seconds"], r["lufs"], r["true_peak_dbtp"], r["ebur128"]["LRA"], r["ebur128"]["I"], r["ebur128"]["TP"], r["stereo_correlation"]), flush=True)


if __name__ == "__main__":
    main()
