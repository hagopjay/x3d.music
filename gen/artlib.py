#!/usr/bin/env python3
"""The AI-made pictures the worlds can use, and the switch that says whether they do.

art/manifest.json names every picture (file, size, sha256 of the file and of the source it was made from, the prompt it came from). Each item has a `use`:
    "ai"           the world draws the generated picture
    "procedural"   the world draws its own picture, made in code (the stand-in that every world was first built with)
The environment variable LOOM_ART overrides every item (LOOM_ART=procedural gives the stand-ins everywhere; LOOM_ART=ai the pictures wherever the file exists), and
LOOM_ART_<ITEM> (item upper-cased, dashes to underscores, e.g. LOOM_ART_DOME_MOTIFS) overrides one. A picture whose file is missing or whose sha256 differs from the manifest is never
used: the item falls back to procedural, and `status()` says why, so a world never builds from a picture nobody can account for.
"""
import hashlib, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.environ.get("LOOM_ART_DIR") or os.path.join(ROOT, "art")       # a scratch folder can stand in for art/ while a new set is tried


def manifest(art_dir=None):
    p = os.path.join(art_dir or ART, "manifest.json")
    if not os.path.isfile(p):
        return {"items": {}}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wanted(item, art_dir=None):
    """What the manifest and the environment ask for: 'ai' or 'procedural'."""
    env = os.environ.get("LOOM_ART_" + item.upper().replace("-", "_")) or os.environ.get("LOOM_ART")
    if env in ("ai", "procedural"):
        return env
    return manifest(art_dir).get("items", {}).get(item, {}).get("use", "procedural")


def status(item, art_dir=None):
    """(use, why): what a world will really draw for this item and the reason. The file must exist and match the manifest's sha256."""
    art_dir = art_dir or ART
    want = wanted(item, art_dir)
    it = manifest(art_dir).get("items", {}).get(item)
    if want == "procedural":
        return "procedural", "asked for" if it else "no such item in the manifest"
    if not it:
        return "procedural", "no such item in the manifest"
    path = os.path.join(art_dir, it["file"])
    if not os.path.isfile(path):
        return "procedural", "file missing: %s" % it["file"]
    if sha256_file(path) != it["sha256"]:
        return "procedural", "sha256 differs from the manifest: %s" % it["file"]
    return "ai", "ok"


def use(item, art_dir=None):
    return status(item, art_dir)[0]


def path(item, art_dir=None):
    it = manifest(art_dir).get("items", {})[item]
    return os.path.join(art_dir or ART, it["file"])


if __name__ == "__main__":
    for k in sorted(manifest().get("items", {})):
        print("%-14s %-11s %s" % (k, *status(k)))
