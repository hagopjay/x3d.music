#!/usr/bin/env python3
"""The Ear witness: does the audio do what the spec says, measured by tools that did not make it?

    python3 -I witnesses/ear.py --piece turca|ode|all [--audio build/audio] [--out build/runs/ear.json]

It reads  <audio>/<piece>/<piece>.master.wav  and  <audio>/<piece>/stems/*.wav  and the score card, and checks:
  E1  the master is 48 kHz stereo 24-bit and as long as the card plus a ring-out; every stem has the master's format and length
  E2  loudness -14 LUFS +-1 by pyloudnorm and by ffmpeg's ebur128 (a second tool), and the two agree to 0.3 LU
  E3  true peak at or under -1.0 dBTP by our own 4x oversampling and by ffmpeg, sample peak under -1 dBFS
  E4  loudness range 4 to 12 LU (ffmpeg, EBU R128)
  E5  no clipped sample in the master or in any stem, no NaN, no DC offset over 0.001
  E6  mean stereo correlation at least 0.2, and no more than 5 percent of the blocks out of phase
  E7  onsets: the drums and the piano start where the score says (median error 5 ms or less, 95th percentile 15 ms or less), measured on the stems with a detector whose window fits the attack
  E8  the master is the stems: aligned to 0.2 ms and 0.9 correlated with their sum
  E9  no sub rumble: the 20 to 60 Hz band is at least 6 dB under the 60 to 250 Hz band
  E10 the piece ends in a ring-out and not a cut: the last 100 ms of the master are under -50 dBFS

check(...) returns the results so tests can feed it damaged audio and see it go red. Needs numpy, scipy, soundfile, pyloudnorm and ffmpeg (requirements-audio.txt).
"""
import argparse, json, os, sys

import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "audio"))
import meter                                       # noqa: E402  (measurements shared with the mix; every number it gives is cross-checked here against ffmpeg)

SR = 48000
LUFS_TARGET, LUFS_TOL, TOOLS_AGREE = -14.0, 1.0, 0.3
TP_MAX, LRA_RANGE, CORR_MIN = -1.0, (4.0, 12.0), 0.2
ONSET_MEDIAN_MS, ONSET_P95_MS, ONSET_MIN = 5.0, 15.0, 20
CLIP = 0.9999
# which stems are checked for onsets, and the detector window that fits their attack: impulsive hits need a short window, the piano's hammer-and-string attack a long one
IMPULSIVE = dict(n_fft=128, hop=12, fmin=1000)
PIANO = dict(n_fft=1024, hop=24, fmin=1000)
ONSET_STEMS = {"turca": (("pno", PIANO), ("kick", IMPULSIVE), ("snare", IMPULSIVE)), "ode": (("kick", IMPULSIVE), ("snare", IMPULSIVE))}


class Results(list):
    def add(self, cid, claim, ok, detail=""):
        self.append({"id": cid, "claim": claim, "ok": bool(ok), "detail": detail})


def onset_errors(x, times, span=0.03, n_fft=256, hop=12, fmin=1000):
    """For each expected onset time (s), the error (s) of the strongest rise of the log-magnitude spectrum above fmin within +-span of it. Only the 2*span around each time is analysed."""
    x = np.asarray(x, dtype="float64")
    if x.ndim == 2:
        x = x.mean(axis=1)
    top = np.abs(x).max()
    if top > 0:
        x = x / top
    win = np.hanning(n_fft + 1)[:-1]
    keep = np.fft.rfftfreq(n_fft, 1.0 / SR) >= fmin
    half = n_fft // 2
    nfr = int(round(2 * span * SR / hop)) + 1
    errs = []
    for t in times:
        c = int(round(t * SR))
        first = c - int(round(span * SR)) - hop                  # one frame ahead of the window, for the difference
        starts = first - half + hop * np.arange(nfr + 1)
        lo, hi = starts[0], starts[-1] + n_fft
        seg = np.zeros(hi - lo)
        a, b = max(lo, 0), min(hi, len(x))
        if b > a:
            seg[a - lo:b - lo] = x[a:b]
        frames = np.lib.stride_tricks.sliding_window_view(seg, n_fft)[::hop][:nfr + 1]
        mag = np.log1p(1000.0 * np.abs(np.fft.rfft(frames * win, axis=1))[:, keep])
        flux = np.maximum(0.0, np.diff(mag, axis=0)).sum(axis=1)
        errs.append(((first + (int(np.argmax(flux)) + 1) * hop) - c) / SR)
    return np.array(errs)


def expected_onsets(card, inst, isolation=0.06):
    """Distinct onset times of an instrument in the card: no grace notes, no arpeggiated chords, and only those with no other onset of that instrument within `isolation` seconds."""
    ts = np.array(sorted({round(n["t"], 6) for n in card["notes"] if n["inst"] == inst and not n.get("g") and "a" not in n.get("art", "")}))
    return np.array([t for i, t in enumerate(ts) if (i == 0 or t - ts[i - 1] > isolation) and (i == len(ts) - 1 or ts[i + 1] - t > isolation)])


def best_lag(a, b, max_lag_s=0.1, down=4):
    """Lag (s) of b against a (positive: b is late) and the correlation there, from the mono signals decimated by `down`."""
    a, b = signal.decimate(a, down, zero_phase=True), signal.decimate(b, down, zero_phase=True)
    m = int(max_lag_s * SR / down)
    n = min(len(a), len(b))
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    full = signal.fftconvolve(a, b[::-1], mode="full")
    mid = n - 1
    seg = full[mid - m:mid + m + 1]
    k = int(np.argmax(seg)) - m                                  # full[mid + k] = sum a[i + k] b[i]: positive k means a is late, i.e. b is early
    lag = -k
    sh = slice(max(0, lag), n + min(0, lag))
    sa = slice(max(0, -lag), n + min(0, -lag))
    corr = float(np.corrcoef(a[sh], b[sa])[0, 1]) if (sh.stop - sh.start) > 10 else 0.0
    return lag * down / SR, corr


def check(card, piece, master_path, stems_dir, onset_stems=None):
    R = Results()
    info = sf.info(master_path)
    master, sr = sf.read(master_path, dtype="float64")
    seconds = card["checks"]["seconds"]
    dur = len(master) / sr if sr else 0.0
    stem_files = sorted(f for f in os.listdir(stems_dir) if f.endswith(".wav")) if os.path.isdir(stems_dir) else []
    odd = []
    for f in stem_files:
        si = sf.info(os.path.join(stems_dir, f))
        if (si.samplerate, si.channels, si.subtype, si.frames) != (info.samplerate, info.channels, info.subtype, info.frames):
            odd.append(f)
    declared = {i["id"] for i in card["instruments"] if i["layer"] == "arrangement" or i["id"] in {n["inst"] for n in card["notes"] if n["layer"] == "composer"}}
    sounding = {os.path.splitext(f)[0] for f in stem_files if not f.startswith("fx_")}
    ok1 = info.samplerate == SR and info.channels == 2 and info.subtype == "PCM_24" and seconds <= dur <= seconds + 15 and not odd and bool(stem_files)
    R.add("E1", "the master is 48 kHz stereo 24-bit and as long as the card plus a ring-out of up to 15 s; every stem has the same format and length; stems exist",
          ok1, "%d Hz, %d ch, %s, %.2f s (card %.2f s); %d stems, %d unlike the master%s" % (info.samplerate, info.channels, info.subtype, dur, seconds, len(stem_files), len(odd), (": " + ", ".join(odd[:3])) if odd else ""))
    if info.samplerate != SR or info.channels != 2:
        return R                                                 # nothing below means anything on another format
    # --- loudness, true peak, range: ours and a second tool's
    lu_a = meter.lufs(master)
    ff = meter.ebur128(master_path)
    R.add("E2", "integrated loudness is -14 LUFS +-1 by pyloudnorm and by ffmpeg, and the two tools agree to 0.3 LU", abs(lu_a - LUFS_TARGET) <= LUFS_TOL and abs(ff["I"] - LUFS_TARGET) <= LUFS_TOL and abs(lu_a - ff["I"]) <= TOOLS_AGREE,
          "pyloudnorm %.2f, ffmpeg %.1f" % (lu_a, ff["I"]))
    tp = meter.true_peak_db(master)
    sp = meter.sample_peak_db(master)
    R.add("E3", "true peak is at or under -1.0 dBTP by our 4x oversampling and by ffmpeg, and the sample peak is under -1 dBFS", tp <= TP_MAX and ff["TP"] <= TP_MAX and sp <= -1.0,
          "ours %.2f dBTP, ffmpeg %.1f dBTP, sample peak %.2f dBFS" % (tp, ff["TP"], sp))
    R.add("E4", "loudness range is between %g and %g LU (ffmpeg, EBU R128)" % LRA_RANGE, LRA_RANGE[0] <= ff["LRA"] <= LRA_RANGE[1], "LRA %.1f LU" % ff["LRA"])
    # --- clipping, NaN, DC in the master and every stem
    bad_stems, dc_bad = [], []
    worst_dc = float(np.abs(master.mean(axis=0)).max())
    clipped = int((np.abs(master) >= CLIP).sum())
    nonfinite = int((~np.isfinite(master)).sum())
    for f in stem_files:
        x, _ = sf.read(os.path.join(stems_dir, f), dtype="float64")
        c = int((np.abs(x) >= CLIP).sum())
        if c:
            bad_stems.append("%s:%d" % (f, c))
        d = float(np.abs(x.mean(axis=0)).max())
        worst_dc = max(worst_dc, d)
        nonfinite += int((~np.isfinite(x)).sum())
    R.add("E5", "no clipped sample in the master or any stem, no NaN or infinity, no DC offset over 0.001", not clipped and not bad_stems and not nonfinite and worst_dc <= 0.001,
          "master clipped samples %d; stems clipped %s; non-finite %d; worst DC %.5f" % (clipped, bad_stems[:4] or "none", nonfinite, worst_dc))
    # --- stereo
    n = int(0.4 * SR)
    blocks = []
    for i in range(0, len(master) - n, n):
        l, r = master[i:i + n, 0], master[i:i + n, 1]
        if np.sqrt((l ** 2 + r ** 2).mean() / 2) < 1e-3 or l.std() < 1e-9 or r.std() < 1e-9:
            continue
        blocks.append(float(np.corrcoef(l, r)[0, 1]))
    mean_c = float(np.mean(blocks)) if blocks else 1.0
    out_of_phase = float(np.mean(np.array(blocks) < 0)) if blocks else 0.0
    R.add("E6", "mean stereo correlation is at least %.1f and no more than 5 percent of the 400 ms blocks are out of phase" % CORR_MIN, mean_c >= CORR_MIN and out_of_phase <= 0.05,
          "mean %.3f over %d blocks, %.1f%% below zero" % (mean_c, len(blocks), 100 * out_of_phase))
    # --- onsets against the score
    rows, ok7 = [], True
    for inst, params in (onset_stems if onset_stems is not None else ONSET_STEMS[piece]):
        path = os.path.join(stems_dir, inst + ".wav")
        exp = expected_onsets(card, inst)
        if not os.path.exists(path) or len(exp) < ONSET_MIN:
            ok7 = False
            rows.append("%s: %s" % (inst, "no stem" if not os.path.exists(path) else "only %d isolated onsets" % len(exp)))
            continue
        x, _ = sf.read(path, dtype="float32")
        e = np.abs(onset_errors(x, exp, **params))
        med, p95 = 1000 * float(np.median(e)), 1000 * float(np.percentile(e, 95))
        ok7 = ok7 and med <= ONSET_MEDIAN_MS and p95 <= ONSET_P95_MS
        rows.append("%s %d onsets: median %.1f ms, p95 %.1f ms" % (inst, len(exp), med, p95))
    R.add("E7", "drum and piano onsets start where the score says: median error %g ms or less and 95th percentile %g ms or less, each with at least %d isolated onsets" % (ONSET_MEDIAN_MS, ONSET_P95_MS, ONSET_MIN),
          ok7, "; ".join(rows))
    # --- the master is the stems
    total = np.zeros((len(master),), dtype="float64")
    for f in stem_files:
        x, _ = sf.read(os.path.join(stems_dir, f), dtype="float32")
        total[:len(x)] += x.mean(axis=1)[:len(total)]
    lag, corr = best_lag(master.mean(axis=1), total)
    R.add("E8", "the master is the stems: their sum, aligned to 0.2 ms, is at least 0.9 correlated with it", abs(lag) <= 0.0002 and corr >= 0.9, "lag %+.2f ms, correlation %.3f" % (1000 * lag, corr))
    # --- balance and ending
    bands = meter.band_levels(master)
    sub, bass = bands["sub 20-60"], bands["bass 60-250"]
    R.add("E9", "no sub rumble: the 20 to 60 Hz band sits at least 6 dB under the 60 to 250 Hz band", sub - bass <= -6.0, "bands re the loudest: %s" % json.dumps(bands))
    tail = master[-int(0.1 * SR):]
    tail_db = float(20 * np.log10(max(np.sqrt((tail ** 2).mean()), 1e-9)))
    R.add("E10", "the piece ends in a ring-out and not a cut: the last 100 ms are under -50 dBFS", tail_db <= -50.0, "last 100 ms %.1f dBFS" % tail_db)
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--piece", default="all", choices=["turca", "ode", "all"])
    ap.add_argument("--audio", default=os.path.join(ROOT, "build", "audio"))
    ap.add_argument("--out")
    a = ap.parse_args()
    pieces = ["turca", "ode"] if a.piece == "all" else [a.piece]
    allr, failed = {}, 0
    for p in pieces:
        card = json.load(open(os.path.join(ROOT, "score", p + ".score.json"), encoding="utf-8"))
        R = check(card, p, os.path.join(a.audio, p, p + ".master.wav"), os.path.join(a.audio, p, "stems"))
        allr[p] = list(R)
        for r in R:
            print("%s %-5s %-4s %s  [%s]" % ("PASS" if r["ok"] else "FAIL", p, r["id"], r["claim"], r["detail"]))
            failed += not r["ok"]
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(allr, open(a.out, "w"), indent=1)
    print("ear witness: %d checks, %d failed" % (sum(len(v) for v in allr.values()), failed))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
