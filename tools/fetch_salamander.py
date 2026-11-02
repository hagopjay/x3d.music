#!/usr/bin/env python3
"""Fetch the Salamander Grand Piano V3 samples the Turca needs into a local cache and check each file against sources/salamander.manifest.json (size and sha256). Standard library only.

The piano is Alexander Holm's Salamander Grand Piano V3 (a Yamaha C5, 48 kHz 24-bit), remapped to SFZ and FLAC by kinwie, licensed CC BY 3.0 (NOTICE.md carries the credit).
Nothing is committed: the subset is about 230 MB. The Turca's notes run from MIDI 38 to 88, which the 17 sampled keys D#2 to D#6 cover, and the card's velocities run from about 36 to 114,
so every second one of the 16 recorded velocity layers is enough (v2 to v16) when the sampler blends the two layers either side of a velocity.

    python3 -I tools/fetch_salamander.py [--cache DIR] [--write-manifest]

--write-manifest records size and sha256 of what was fetched (do this once, in its own commit). The cache defaults to $LOOMSONG_CACHE/salamander, else ~/.cache/loomsong/salamander.
"""
import argparse, hashlib, json, os, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = "https://raw.githubusercontent.com/sfzinstruments/SalamanderGrandPiano/master/"
MANIFEST = os.path.join(ROOT, "sources", "salamander.manifest.json")
KEYS = ["D#2", "F#2", "A2", "C3", "D#3", "F#3", "A3", "C4", "D#4", "F#4", "A4", "C5", "D#5", "F#5", "A5", "C6", "D#6"]
LAYERS = [2, 4, 6, 8, 10, 12, 14, 16]


def default_cache():
    return os.path.join(os.environ.get("LOOMSONG_CACHE") or os.path.expanduser("~/.cache/loomsong"), "salamander")


def names():
    return ["Samples/%sv%d.flac" % (k, v) for k in KEYS for v in LAYERS]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_one(args):
    rel, cache = args
    dest = os.path.join(cache, rel)
    if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
        return rel, "cached"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    url = BASE + urllib.parse.quote(rel)
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "loomsong-fetch"}), timeout=25) as r:
                data = r.read()
            if data[:4] != b"fLaC":
                raise ValueError("not a FLAC file (%d bytes)" % len(data))
            tmp = dest + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, dest)
            return rel, "fetched"
        except Exception as e:                                   # network errors are retried; the last one is reported
            last = e
            time.sleep(2 ** attempt)
    return rel, "FAILED: %s" % last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=default_cache())
    ap.add_argument("--write-manifest", action="store_true")
    a = ap.parse_args()
    todo = [(n, a.cache) for n in names()]
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(fetch_one, todo))
    bad = [r for r in results if r[1].startswith("FAILED")]
    for rel, why in bad:
        print("  %s  %s" % (rel, why))
    if bad:
        print("fetch_salamander: %d of %d files failed" % (len(bad), len(results)))
        return 1
    files = {rel: {"bytes": os.path.getsize(os.path.join(a.cache, rel)), "sha256": sha256_file(os.path.join(a.cache, rel))} for rel, _ in todo}
    if a.write_manifest:
        doc = {"source": BASE, "licence": "CC BY 3.0 (Alexander Holm; SFZ and FLAC remap by kinwie)", "keys": KEYS, "layers": LAYERS, "files": files}
        with open(MANIFEST, "w") as f:
            json.dump(doc, f, indent=1, sort_keys=True)
            f.write("\n")
        print("fetch_salamander: wrote %s (%d files, %.1f MB)" % (os.path.relpath(MANIFEST, ROOT), len(files), sum(v["bytes"] for v in files.values()) / 1e6))
        return 0
    want = json.load(open(MANIFEST))["files"]
    wrong = [rel for rel, v in files.items() if want.get(rel) != v]
    for rel in wrong:
        os.remove(os.path.join(a.cache, rel))
    if wrong or set(want) != set(files):
        print("fetch_salamander: %d files differ from the manifest (deleted from the cache; run again)" % len(wrong))
        return 1
    print("fetch_salamander: %d files in %s, all match the manifest (%.1f MB)" % (len(files), a.cache, sum(v["bytes"] for v in files.values()) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
