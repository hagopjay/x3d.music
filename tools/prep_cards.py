#!/usr/bin/env python3
"""Make the page's cards from the generated animated pictures: video only, sized for a web page, stripped to pixels, each with a poster.

    python3 -I tools/prep_cards.py --src DIR [--out build/media] [--width 1600] [--crf 30]
    python3 -I tools/prep_cards.py --synthetic [--out build/media]

DIR holds the generated animated pictures as <name>-final1080.mp4 (or <name>-draft720.mp4 where no final was made). They are AI-made, much too big for a web page (27 to 36 MB each) and are not kept
in this repository, nor are the cards made from them: the repository holds this tool and the manifest's description, and a build finds the cards in --out (default build/media, or the folder
LOOM_MEDIA names). A build without cards is a page without cards (page/cards.js does nothing, the worlds are untouched).

    title    still1-title            the card behind the title and the Play button
    ode      still2-ode-open         the Ode's opening
    turca    still3-turca-open       the Rondo's opening
    between  still4-intermission     the card behind the end card (the hall between the pieces)

Each card becomes <id>.mp4 (H.264, no sound, every tag of the original dropped and no encoder string or settings line written, our own one-line comment "AI-made: ...") and <id>.jpg (its first frame, a poster for while the video loads; pixels
only, one comment "AI-made: ..." that witnesses/leak_sweep.py accepts). media/cards.json records sizes and sha256 of every file and of its source; page/build_page.py ships a card only when both of its
files match.

--synthetic makes four two-second test patterns instead (no source needed), marked "synthetic" in the manifest: the page shows them as test patterns and never calls them AI-made. CI uses them to
exercise the card code on every build.
"""
import argparse, hashlib, io, json, os, shutil, subprocess, sys, tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "witnesses"))
import leak_sweep as LS            # noqa: E402

CARDS = [("title", "still1-title"), ("ode", "still2-ode-open"), ("turca", "still3-turca-open"), ("between", "still4-intermission")]
LABEL = "AI-made: an animated picture, see docs/PROMPTS.md"
SYN_LABEL = "Test pattern: a stand-in for an animated picture, not AI-made"
POSTER_W = 1280
MAX_VIDEO = 6 * 1024 * 1024         # a card above this is a mistake (the page budget is 64 MB for everything; the repository's media cap is 5 MB and cards stay out of it)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit("%s failed: %s" % (cmd[0], r.stderr.strip()[:600]))
    return r.stdout


def probe(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,codec_name,nb_frames:format=duration", "-of", "json", path])
    j = json.loads(out)
    s = j["streams"][0]
    return dict(width=int(s["width"]), height=int(s["height"]), codec=s["codec_name"], seconds=round(float(j["format"]["duration"]), 2))


def encode(src, dst, width, crf, label):
    """Video only, scaled to `width`, H.264 yuv420p, faststart. Two steps so that nothing but our comment is left in the file: the encode drops every tag of the source and every SEI unit (the encoder's
    settings line is one), then a copy into a fresh container drops the encoder string the encoder writes into its own stream (and writes none of its own: bitexact)."""
    mid = dst + ".tmp.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-an", "-map", "0:v:0", "-map_metadata", "-1", "-map_chapters", "-1",
         "-vf", "scale=%d:-2:flags=lanczos,format=yuv420p" % width,
         "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-profile:v", "high", "-x264-params", "keyint=48:min-keyint=24",
         "-bsf:v", "filter_units=remove_types=6", "-movflags", "+faststart", mid])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", mid, "-c", "copy", "-map", "0:v:0", "-map_metadata", "-1", "-map_chapters", "-1",
         "-fflags", "+bitexact", "-flags", "+bitexact", "-movflags", "+faststart", "-metadata", "comment=" + label, dst])
    os.remove(mid)


def poster(video, label):
    """The first frame as a JPEG made from raw pixels (no chunk of the video's can follow it) with our one comment."""
    with tempfile.TemporaryDirectory() as d:
        png = os.path.join(d, "f.png")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-frames:v", "1", png])
        with Image.open(png) as im:
            im = im.convert("RGB")
            im = Image.frombytes("RGB", im.size, im.tobytes())
    if im.size[0] > POSTER_W:
        im = im.resize((POSTER_W, round(im.size[1] * POSTER_W / im.size[0])), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True, comment=label.encode("ascii"))
    return buf.getvalue()


def synthetic_source(path, k, seconds=2):
    """A two-second test pattern, a different hue for each card."""
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24:duration=%d" % seconds,
         "-vf", "hue=h=%d" % (90 * k), "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", path])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "media"))
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--crf", type=int, default=30)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args(argv)
    if not a.synthetic and not a.src:
        sys.exit("give --src DIR (the generated animated pictures) or --synthetic")
    shutil.rmtree(a.out, ignore_errors=True)
    os.makedirs(a.out)
    label = SYN_LABEL if a.synthetic else LABEL
    man = {"schema": "loomsong.cards/1", "synthetic": bool(a.synthetic),
           "note": "Cards for the page: AI-made animated pictures, re-encoded for the web (video only). Built by tools/prep_cards.py; page/build_page.py ships a card only when its files match this manifest.",
           "cards": {}}
    tmp = tempfile.mkdtemp()
    try:
        for k, (cid, stem) in enumerate(CARDS):
            if a.synthetic:
                src = os.path.join(tmp, stem + ".mp4")
                synthetic_source(src, k)
                kind = "synthetic"
            else:
                src = None
                for kind in ("final1080", "draft720"):
                    p = os.path.join(a.src, "%s-%s.mp4" % (stem, kind))
                    if os.path.isfile(p):
                        src = p
                        break
                if not src:
                    print("%-8s no source in %s: left out" % (cid, a.src))
                    continue
            dst = os.path.join(a.out, cid + ".mp4")
            width = 640 if a.synthetic else a.width
            encode(src, dst, width, a.crf, label)
            n = os.path.getsize(dst)
            if n > MAX_VIDEO:
                sys.exit("%s is %d bytes: over the card limit; raise --crf or lower --width" % (cid, n))
            pic = poster(dst, label)
            with open(os.path.join(a.out, cid + ".jpg"), "wb") as f:
                f.write(pic)
            hits = LS.scan_image(cid + ".jpg", pic)
            if hits:
                sys.exit("poster %s is not clean: %s" % (cid, hits))
            pr = probe(dst)
            man["cards"][cid] = dict(video=cid + ".mp4", poster=cid + ".jpg", seconds=pr["seconds"], size=[pr["width"], pr["height"]], bytes=n, poster_bytes=len(pic),
                                     sha256=sha_file(dst), poster_sha256=sha_bytes(pic), source=os.path.basename(src)[:-4], source_kind=kind, source_sha256=sha_file(src),
                                     prompt_id=stem, label=label)
            print("%-8s %-28s -> %-11s %8d bytes  %dx%d  %.1f s  poster %6d bytes" % (cid, os.path.basename(src), cid + ".mp4", n, pr["width"], pr["height"], pr["seconds"], len(pic)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(os.path.join(a.out, "cards.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, indent=1)
        f.write("\n")
    print("manifest:", os.path.join(a.out, "cards.json"), "(%d cards, %s)" % (len(man["cards"]), "synthetic test patterns" if a.synthetic else "AI-made"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
