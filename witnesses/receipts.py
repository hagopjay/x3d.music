#!/usr/bin/env python3
"""Loomsong receipts for generated files: what made them, written beside them, and a check that a rebuild gives the same bytes. Stdlib only.

    python3 -I witnesses/receipts.py write receipts/NAME.json --cmd "python3 -I gen/probes/make_probes.py" --inputs F [F ...] --outputs G [G ...] [--force] [--note TEXT]
    python3 -I witnesses/receipts.py check receipts/NAME.json [...]

write records the command, SOURCE_DATE_EPOCH, the Python version, and the sha256 and size of every input and output. It will not overwrite a receipt without --force: a receipt is a
record of a run, not a cache. check hashes the inputs (a changed input means the receipt is out of date, which is reported as such), runs the command again, and compares every output
hash. Exit 1 on a drift. A note given with --note is stored in the receipt and printed with a drift: it says when a drift is expected (the audio masters match only on the machine class that made them). Paths are relative to the repository root. Blender assets keep the Loom's own receipt (loom_receipt.py); this one is for files the generators write.
"""
import argparse, hashlib, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPOCH = "1793491200"                                        # 2026-11-01T00:00:00Z, the same default as gen/x3dw.py


def sha(p):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, p), "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def entry(p):
    return {"path": p, "sha256": sha(p), "bytes": os.path.getsize(os.path.join(ROOT, p))}


def run(cmd):
    env = dict(os.environ, SOURCE_DATE_EPOCH=EPOCH)
    r = subprocess.run(cmd, shell=True, cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    if r.returncode:
        sys.exit("command failed (%d): %s\n%s" % (r.returncode, cmd, (r.stderr or r.stdout)[-600:]))


def write(a):
    out = os.path.join(ROOT, a.receipt)
    if os.path.exists(out) and not a.force:
        sys.exit("%s exists; a receipt is a record of a run (use --force to replace it)" % a.receipt)
    run(a.cmd)
    rec = {"schema": "loomsong.receipt/1", "command": a.cmd, "SOURCE_DATE_EPOCH": EPOCH, "python": "%d.%d" % sys.version_info[:2],
           "inputs": [entry(p) for p in a.inputs], "outputs": [entry(p) for p in a.outputs]}
    if a.note:
        rec["note"] = a.note
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="\n") as f:
        json.dump(rec, f, indent=1)
        f.write("\n")
    print("wrote %s: %d inputs, %d outputs" % (a.receipt, len(rec["inputs"]), len(rec["outputs"])))


def check(a):
    bad = 0
    for r in a.receipts:
        with open(os.path.join(ROOT, r)) as f:
            rec = json.load(f)
        stale = [i["path"] for i in rec["inputs"] if not os.path.exists(os.path.join(ROOT, i["path"])) or sha(i["path"]) != i["sha256"]]
        if stale:
            print("STALE %s: inputs changed since the receipt was written: %s (rewrite it with --force and note why)" % (r, ", ".join(stale)))
            bad += 1
            continue
        run(rec["command"])
        drift = [o["path"] for o in rec["outputs"] if not os.path.exists(os.path.join(ROOT, o["path"])) or sha(o["path"]) != o["sha256"]]
        print("%s %s: %d outputs rebuilt%s" % ("DRIFT" if drift else "OK   ", r, len(rec["outputs"]), (" (differ: %s)" % ", ".join(drift)) if drift else ", same sha256"))
        if drift and rec.get("note"):
            print("      note: %s" % rec["note"])
        bad += 1 if drift else 0
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    w = sub.add_parser("write")
    w.add_argument("receipt")
    w.add_argument("--cmd", required=True)
    w.add_argument("--inputs", nargs="+", required=True)
    w.add_argument("--outputs", nargs="+", required=True)
    w.add_argument("--force", action="store_true")
    w.add_argument("--note", default="", help="a sentence kept in the receipt, printed when a check drifts")
    c = sub.add_parser("check")
    c.add_argument("receipts", nargs="+")
    a = ap.parse_args()
    if a.mode == "write":
        write(a)
        return 0
    return check(a)


if __name__ == "__main__":
    sys.exit(main())
