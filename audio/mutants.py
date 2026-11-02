#!/usr/bin/env python3
"""Mutation spot-check for the audio tests: break the code on purpose and see whether the tests notice.

A test that cannot fail proves nothing. Each mutant copies audio/ into a scratch folder, changes one expression there (the repository is never touched) and runs the test class of audio/test_audio.py
that should notice. CAUGHT means that run failed on an assertion. BROKEN means it raised an exception instead (a NameError or a syntax error would fail any test, so it proves nothing about this one).
MISSED means every test still passed: a gap in the tests, to be closed. SKIPPED means the text to change was not found (the code moved on; update the mutant).

    python3 -I audio/mutants.py [part of a name ...]       # all of them, or the ones whose name contains the text; about two minutes for all eleven

The sampler and Faust classes read the piano samples, so LOOMSONG_CACHE must point at the folder that tools/fetch_salamander.py filled (or the default cache must exist).
"""
import os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# (name, file, text to change, what it becomes, test class that must fail)
MUTANTS = [
    ("limiter ceiling 3 dB too high", "audio/mix.py", "ceil = 10 ** (ceiling_db / 20)\n    peak = true_peak_envelope", "ceil = 10 ** ((ceiling_db + 3) / 20)\n    peak = true_peak_envelope", "Limiter"),
    ("limiter looks only backwards (latency)", "audio/mix.py", 'low = ndimage.minimum_filter1d(need, size=2 * half + 1, mode="nearest")', 'low = ndimage.minimum_filter1d(need, size=2 * half + 1, mode="nearest", origin=half)', "Limiter"),
    ("ducking depth doubled", "audio/mix.py", "shape = (1.0 - depth * np.exp(", "shape = (1.0 - 2 * depth * np.exp(", "Curves"),
    ("ride sign flipped", "audio/mix.py", "last = arc[key] - meter.lufs(x[i0:i1])", "last = arc[key] + meter.lufs(x[i0:i1])", "Ride"),
    ("velocity blend swapped", "audio/sampler.py", "return [(la, 1.0 - w), (lb, w)]", "return [(la, w), (lb, 1.0 - w)]", "SamplerRules"),
    ("nearest key becomes farthest", "audio/sampler.py", "return min(KEYS.items(), key=lambda kv: (abs(kv[1] - midi), kv[1]))", "return max(KEYS.items(), key=lambda kv: (abs(kv[1] - midi), kv[1]))", "SamplerRules"),
    ("pitch shifted the wrong way", "audio/sampler.py", "ratio = 2.0 ** ((midi - centre) / 12.0)", "ratio = 2.0 ** ((centre - midi) / 12.0)", "SamplerOnSyntheticRecordings"),
    ("arpeggio roll 20 ms instead of 18", "audio/sampler.py", "t += 0.018 * k", "t += 0.020 * k", "SamplerOnSyntheticRecordings"),
    ("routing drops the relative octave", "audio/rack.py", 'pitch=n["pitch"] + 12 * (n.get("oct", 0) + r.get("rel", 0))', 'pitch=n["pitch"] + 12 * (n.get("oct", 0))', "Routing"),
    ("faust note starts 1 ms late", "audio/rack.py", 'float(n["t"]), max(float(n["dur"]), 0.002))', 'float(n["t"]) + 0.001, max(float(n["dur"]), 0.002))', "FaustVoices"),
    ("bass chain gains a 10 ms delay", "audio/recipes.py", "HighpassFilter(24)", 'HighpassFilter(24), __import__("pedalboard").Delay(delay_seconds=0.01, feedback=0.0, mix=1.0)', "Recipes"),
]


def run_one(name, rel, old, new, cls):
    with tempfile.TemporaryDirectory(prefix="loomsong-mutant-") as d:
        shutil.copytree(os.path.join(ROOT, "audio"), os.path.join(d, "audio"), ignore=shutil.ignore_patterns("__pycache__"))
        os.symlink(os.path.join(ROOT, "score"), os.path.join(d, "score"))
        path = os.path.join(d, rel)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if old not in text:
            return "SKIPPED", "text to change not found in " + rel
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(old, new, 1))
        r = subprocess.run([sys.executable, "-I", os.path.join(d, "audio", "test_audio.py"), cls], capture_output=True, text=True)
        lines = (r.stderr + r.stdout).splitlines()
        failed = [l[6:].strip() for l in lines if l.startswith("FAIL:")]
        errored = [l[7:].strip() for l in lines if l.startswith("ERROR:")]
        if r.returncode == 0:
            return "MISSED", "every test in %s still passed" % cls
        if errored or not failed:
            return "BROKEN", "; ".join(errored[:2]) or "the run failed without a failing assertion"
        return "CAUGHT", "; ".join(failed[:2])


def main(argv):
    picked = [m for m in MUTANTS if not argv or any(a in m[0] for a in argv)]
    tally = {}
    for m in picked:
        state, why = run_one(*m)
        tally[state] = tally.get(state, 0) + 1
        print("%-8s %s  <- %s" % (state, m[0], why), flush=True)
    print(", ".join("%d %s" % (v, k.lower()) for k, v in sorted(tally.items())) + " of %d" % len(picked))
    return 0 if tally.get("CAUGHT", 0) == len(picked) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
