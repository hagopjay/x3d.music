"""Measurements on audio, shared by the mix (to aim) and the Ear witness (to judge): loudness, true peak, loudness range, stereo correlation, spectral balance, onsets.

Loudness is measured by two independent tools (pyloudnorm here, ffmpeg's ebur128 in ear.py); the true peak is 4x oversampled as BS.1770 asks.
"""
import re
import subprocess

import numpy as np
from scipy import signal

SR = 48000


def lufs(x):
    """Integrated loudness in LUFS of float audio shaped (n, 2) or (n,): pyloudnorm, BS.1770 gating."""
    import pyloudnorm as pyln
    x = np.asarray(x, dtype="float64")
    return float(pyln.Meter(SR).integrated_loudness(x))


def active_rms_db(x, block=0.1, within=50.0):
    """RMS in dBFS over the 100 ms blocks that are within `within` dB of the loudest block: a quick level for sparse material, which reads as its playing level and not its average over silence.
    Used to bring stems to a common level before their chains; the loudness that matters (LUFS, pyloudnorm) is measured after the chain."""
    n = int(block * SR)
    x = np.asarray(x, dtype="float64")
    if x.ndim == 2:
        x = x.mean(axis=1)
    m = len(x) // n
    p = (x[:m * n].reshape(m, n) ** 2).mean(axis=1)
    top = p.max()
    if top <= 0:
        return -120.0
    keep = p[p > top * 10 ** (-within / 10)]
    return float(10 * np.log10(keep.mean()))


def true_peak_db(x):
    """True peak in dBTP: the largest sample after 4x oversampling (a 24-tap-per-phase polyphase filter), over all channels."""
    x = np.asarray(x, dtype="float64")
    if x.ndim == 1:
        x = x[:, None]
    over = signal.resample_poly(x, 4, 1, axis=0, padtype="line")
    return float(20 * np.log10(max(np.abs(over).max(), 1e-12)))


def sample_peak_db(x):
    return float(20 * np.log10(max(np.abs(x).max(), 1e-12)))


def stereo_correlation(x, block=0.4):
    """Mean Pearson correlation between the channels over 400 ms blocks that are not silent (blocks under -60 dBFS RMS are skipped)."""
    n = int(block * SR)
    vals = []
    for i in range(0, len(x) - n, n):
        l, r = x[i:i + n, 0].astype("float64"), x[i:i + n, 1].astype("float64")
        if np.sqrt((l ** 2 + r ** 2).mean() / 2) < 1e-3 or l.std() < 1e-9 or r.std() < 1e-9:
            continue
        vals.append(float(np.corrcoef(l, r)[0, 1]))
    return float(np.mean(vals)) if vals else 1.0


BANDS = (("sub 20-60", 20, 60), ("bass 60-250", 60, 250), ("low-mid 250-500", 250, 500), ("mid 500-2k", 500, 2000), ("upper-mid 2k-6k", 2000, 6000), ("presence 6k-10k", 6000, 10000), ("air 10k-20k", 10000, 20000))


def band_levels(x):
    """Energy per octave-ish band in dB, relative to the loudest band, from the long-term average power spectrum of the mono mix."""
    mono = np.asarray(x, dtype="float64").mean(axis=1) if x.ndim == 2 else np.asarray(x, dtype="float64")
    f, p = signal.welch(mono, SR, nperseg=8192)
    out = {}
    for name, lo, hi in BANDS:
        sel = (f >= lo) & (f < hi)
        out[name] = float(10 * np.log10(p[sel].sum() * (f[1] - f[0]) + 1e-18))
    top = max(out.values())
    return {k: round(v - top, 1) for k, v in out.items()}


def ebur128(path):
    """Loudness, loudness range and true peak by ffmpeg's ebur128 filter (a tool independent of pyloudnorm): dict(I, LRA, TP) in LUFS, LU, dBTP."""
    r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr.split("Summary:")[-1]
    grab = lambda pat: float(re.search(pat, tail).group(1))
    return {"I": grab(r"I:\s+(-?[\d.]+) LUFS"), "LRA": grab(r"LRA:\s+(-?[\d.]+) LU"), "TP": grab(r"Peak:\s+(-?[\d.]+) dBFS")}
