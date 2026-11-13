#!/usr/bin/env python3
"""Lay out the Moonlight page from the generator, never from stored outputs.

    python3 -I moonlight/page/build_page.py [--out build/pages] [--xite build/xite]

1. build_project.py turns the three event lists into the LMMS project (v1, trims applied).
2. mmp2x3d.xsl turns that project into the X3D scene (lxml / libxslt, XSLT 1.0).
3. The page, the stylesheet, the project, the scene, the master and the pinned X_ITE
   (fetched by tools/fetch_xite.py) are copied into <out>/moonlight/.
4. The sha256 of everything generated is checked against moonlight/receipt.v1.json;
   a mismatch stops the build (--write-receipt records a new one instead).

The master (media/moonlight-two-ways.v1.mp3) is the one rendered by LMMS from this same
project; LMMS and the SoundFont are not in CI, so the receipt pins its bytes instead.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
POC = os.path.dirname(HERE)
ROOT = os.path.dirname(POC)
V = "v1"


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def build_project(dst):
    env = dict(os.environ, TRIMS=os.path.join(POC, "lmms", "trims.json"))
    env.pop("NO_MASTER", None)
    s = os.path.join(POC, "score")
    subprocess.run([sys.executable, "-I", os.path.join(POC, "lmms", "build_project.py"),
                    os.path.join(s, "adagio.events.json"), os.path.join(s, "presto-1-64.events.json"),
                    os.path.join(s, "presto-191-201.events.json"), dst], check=True, env=env,
                   stdout=subprocess.DEVNULL)


def transform(mmp, xsl, dst):
    from lxml import etree
    out = etree.XSLT(etree.parse(xsl))(etree.parse(mmp))
    open(dst, "w").write(str(out))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "pages"))
    ap.add_argument("--xite", default=os.path.join(ROOT, "build", "xite"))
    ap.add_argument("--write-receipt", action="store_true")
    a = ap.parse_args(argv)
    if not os.path.exists(os.path.join(a.xite, "x_ite.min.js")):
        sys.exit("X_ITE missing: run  python3 -I tools/fetch_xite.py  first")

    site = os.path.join(a.out, "moonlight")
    data = os.path.join(site, "data")
    shutil.rmtree(site, ignore_errors=True)
    os.makedirs(data)

    mmp = os.path.join(data, f"moonlight-two-ways.{V}.mmp")
    build_project(mmp)
    xsl = os.path.join(POC, "viz", "mmp2x3d.xsl")
    x3d = os.path.join(data, f"moonlight-two-ways.{V}.x3d.xml")
    transform(mmp, xsl, x3d)
    # the page fetches XML by an extension every static host serves as XML
    shutil.copyfile(mmp, os.path.join(data, f"moonlight-two-ways.{V}.mmp.xml"))
    shutil.copyfile(xsl, os.path.join(data, "mmp2x3d.xsl.xml"))
    shutil.copyfile(os.path.join(POC, "media", f"moonlight-two-ways.{V}.mp3"),
                    os.path.join(data, f"moonlight-two-ways.{V}.mp3"))
    shutil.copyfile(os.path.join(HERE, "index.html"), os.path.join(site, "index.html"))
    shutil.copytree(a.xite, os.path.join(site, "xite"))

    got = {"mmp": sha(mmp), "x3d": sha(x3d), "mp3": sha(os.path.join(data, f"moonlight-two-ways.{V}.mp3"))}
    rp = os.path.join(POC, f"receipt.{V}.json")
    if a.write_receipt:
        rec = {"_note": "sha256 of the v1 outputs. The project and the scene are rebuilt and must match; "
                        "the master is LMMS's render of this project and is pinned as bytes.",
               "inputs": {os.path.relpath(p, ROOT): sha(p) for p in sorted(
                   [os.path.join(POC, "score", f) for f in os.listdir(os.path.join(POC, "score")) if f.endswith(".events.json")]
                   + [os.path.join(POC, "lmms", "build_project.py"), os.path.join(POC, "lmms", "trims.json"), xsl])},
               "outputs": got,
               "render": "lmms render moonlight-two-ways.v1.mmp -f flac (LMMS 1.3.0-alpha, master 5ba6744), "
                         "FluidR3_GM.sf2; ffmpeg libmp3lame 192 kb/s"}
        json.dump(rec, open(rp, "w"), indent=1)
        print("receipt written:", got)
    else:
        want = json.load(open(rp))["outputs"]
        bad = [k for k in want if want[k] != got[k]]
        if bad:
            sys.exit("receipt mismatch: " + ", ".join(f"{k} {got[k][:12]} != {want[k][:12]}" for k in bad))
    # site root: a small landing page that names both proofs of concept
    shutil.copyfile(os.path.join(HERE, "landing.html"), os.path.join(a.out, "index.html"))
    open(os.path.join(a.out, ".nojekyll"), "w").close()
    n = sum(len(fs) for _, _, fs in os.walk(a.out))
    print(f"page built: {a.out} ({n} files), receipt {'written' if a.write_receipt else 'matches'}")


if __name__ == "__main__":
    main()
