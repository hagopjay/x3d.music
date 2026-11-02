#!/usr/bin/env python3
"""Fetch the pinned X_ITE from npm and unpack the subset the page ships as its own files.

    python3 -I tools/fetch_xite.py [--out build/xite] [--tarball PATH]

Checks the tarball against the sha512 in tools/pins.json, copies x_ite.min.js, x_ite.css and the
assets the page needs (components, fonts, lib minus libktx.wasm, images, hatching, linetype),
and writes MANIFEST.json (path, bytes, sha256) beside them. X_ITE is MIT licensed; its LICENSE.md
is copied too. It is never fetched from a CDN at runtime: the host's policy refuses the runtime fetches.
"""
import argparse, base64, hashlib, io, json, os, sys, tarfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def wanted(rel):
    """rel is the path inside dist/."""
    if rel in ("x_ite.min.js", "x_ite.css", "LICENSE.md"):
        return True
    if rel.startswith("assets/components/") and rel.endswith(".min.js"):
        return True
    if rel.startswith("assets/fonts/"):
        return True
    if rel.startswith("assets/lib/"):
        return rel != "assets/lib/libktx.wasm"
    return rel.startswith(("assets/images/", "assets/hatching/", "assets/linetype"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "xite"))
    ap.add_argument("--tarball")
    a = ap.parse_args(argv)
    pins = json.load(open(os.path.join(HERE, "pins.json")))["x_ite"]
    data = open(a.tarball, "rb").read() if a.tarball else urllib.request.urlopen(pins["tarball"], timeout=120).read()
    algo, _, want = pins["integrity"].partition("-")
    got = base64.b64encode(hashlib.new(algo, data).digest()).decode()
    if got != want:
        sys.exit("integrity mismatch for x_ite %s: got %s-%s" % (pins["version"], algo, got))
    out, manifest = a.out, []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        for m in sorted(tf.getmembers(), key=lambda m: m.name):
            if not m.isfile() or not m.name.startswith("package/dist/"):
                continue
            rel = m.name[len("package/dist/"):]
            if not wanted(rel):
                continue
            b = tf.extractfile(m).read()
            dst = os.path.join(out, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(b)
            manifest.append({"path": rel, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    json.dump({"x_ite": pins["version"], "integrity": pins["integrity"], "files": manifest}, open(os.path.join(out, "MANIFEST.json"), "w"), indent=1)
    print("x_ite %s: %d files, %.1f MB -> %s" % (pins["version"], len(manifest), sum(f["bytes"] for f in manifest) / 1e6, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
