#!/usr/bin/env python3
"""Make the repository's art from the generated pictures: strip them to pixels, size them, build the dome's motif atlas, write art/manifest.json.

    python3 -I tools/prep_art.py --src DIR [--out art] [--tapestry tapestry-cand-1]

DIR holds the generated pictures as motif-A.png .. motif-L.png (twelve square Iznik-style tiles) and tapestry-cand-<n>.png (3:4). They are AI-made and are not kept in the repository: only what the
worlds read is, and every file is rebuilt from pixels alone (a new image from the raw bytes, so no chunk, no EXIF, no XMP, no content-credentials block of the original can follow it).
Each output holds one line of our own, "AI-made: ...", which witnesses/leak_sweep.py accepts and nothing else.

    art/ode-tapestry.png    the tapestry's picture, 512 x 768. gen/picture_ode.py weaves it: each cell takes the nearest of the five threads (quantize()).
    art/dome-motifs.jpg     the dome's twelve motifs as an atlas of 4 x 3 tiles of 512 px, each tile its picture (480 px) in a 16 px gutter of its own mirror image, so a texture filter never
                            reads a neighbour's colour and the dome can sample every tile mirrored (no seam to hide). Tile order is the motif letters A..L, row by row from the top left.
    art/manifest.json       file, size, sha256 of each file and of each source, and `use` (ai or procedural), the switch gen/artlib.py reads.

The prompts that made the pictures, with the sha256 of each prompt as it was sent, are in docs/PROMPTS.md.
"""
import argparse, hashlib, io, json, os, sys

import numpy as np
from PIL import Image, PngImagePlugin

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "witnesses"))
import leak_sweep as LS            # noqa: E402

LABEL = "AI-made: a generated picture, see docs/PROMPTS.md"
TAP_SIZE = (512, 768)
TILE, GUT, COLS, ROWS = 512, 16, 4, 3
INNER = TILE - 2 * GUT
MOTIFS = "ABCDEFGHIJKL"
MAX_BYTES = 5 * 1024 * 1024        # the repository's cap for media (the spec)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pixels(path):
    """The picture as a bare RGB image: made from the raw bytes, so nothing of the file's own metadata can come along."""
    with Image.open(path) as im:
        im = im.convert("RGB")
        return Image.frombytes("RGB", im.size, im.tobytes())


def png_bytes(im):
    info = PngImagePlugin.PngInfo()
    info.add_text("Comment", LABEL)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True, pnginfo=info)
    return buf.getvalue()


def jpeg_bytes(im, quality=86):
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, subsampling=0, optimize=True, progressive=False, comment=LABEL.encode("ascii"))
    return buf.getvalue()


def tapestry(src_png):
    im = pixels(src_png)
    assert abs(im.size[0] / im.size[1] - 0.75) < 0.01, "the tapestry's picture must be 3:4, got %s" % (im.size,)
    return png_bytes(im.resize(TAP_SIZE, Image.LANCZOS))


def tile_with_gutter(im):
    """One motif: centre-cropped square, INNER px, in a GUT px frame that is its own mirror image (the edge pixel repeated once, as a mirrored texture lookup reads it)."""
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((INNER, INNER), Image.LANCZOS)
    a = np.asarray(im)
    return np.pad(a, ((GUT, GUT), (GUT, GUT), (0, 0)), mode="symmetric")


def atlas(src_dir):
    out = np.zeros((ROWS * TILE, COLS * TILE, 3), np.uint8)
    sources = {}
    for i, letter in enumerate(MOTIFS):
        p = os.path.join(src_dir, "motif-%s.png" % letter)
        sources["motif-" + letter] = sha(open(p, "rb").read())
        r, c = divmod(i, COLS)
        out[r * TILE:(r + 1) * TILE, c * TILE:(c + 1) * TILE] = tile_with_gutter(pixels(p))
    return jpeg_bytes(Image.fromarray(out)), sources


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "art"))
    ap.add_argument("--tapestry", default="tapestry-cand-1")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    man = {"schema": "loomsong.art/1",
           "note": "AI-made pictures the worlds can use. `use` is the switch gen/artlib.py reads (ai or procedural); the prompts are in docs/PROMPTS.md.",
           "items": {}}
    tp = os.path.join(a.src, a.tapestry + ".png")
    tdata = tapestry(tp)
    open(os.path.join(a.out, "ode-tapestry.png"), "wb").write(tdata)
    man["items"]["ode-tapestry"] = {"file": "ode-tapestry.png", "use": "ai", "size": list(TAP_SIZE), "bytes": len(tdata), "sha256": sha(tdata),
                                    "prompt_id": a.tapestry, "source_sha256": sha(open(tp, "rb").read()), "label": LABEL}
    adata, sources = atlas(a.src)
    open(os.path.join(a.out, "dome-motifs.jpg"), "wb").write(adata)
    man["items"]["dome-motifs"] = {"file": "dome-motifs.jpg", "use": "ai", "size": [COLS * TILE, ROWS * TILE], "bytes": len(adata), "sha256": sha(adata),
                                   "atlas": {"cols": COLS, "rows": ROWS, "tile": TILE, "gutter": GUT, "order": ["motif-" + c for c in MOTIFS]},
                                   "prompt_ids": ["motif-" + c for c in MOTIFS], "source_sha256": sources, "label": LABEL}
    with open(os.path.join(a.out, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, indent=1, sort_keys=False)
        f.write("\n")
    bad = []
    for name in ("ode-tapestry.png", "dome-motifs.jpg"):
        p = os.path.join(a.out, name)
        data = open(p, "rb").read()
        hits = LS.scan_image(name, data)
        if hits or len(data) > MAX_BYTES:
            bad.append((name, hits, len(data)))
        print("%-18s %9d bytes  %s" % (name, len(data), "clean" if not hits else hits))
    if bad:
        sys.exit("art not clean or too big: %s" % bad)
    print("manifest:", os.path.join(a.out, "manifest.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
