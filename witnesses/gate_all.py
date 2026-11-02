#!/usr/bin/env python3
"""Grammar, Meaning and Traps over every .x3d in a folder: the pinned fork validator (XSD, semantic checks, profile), the Loom's gate and the five Loomsong rules.

    python3 -I witnesses/gate_all.py DIR [--out build/runs/gate.json]

Environment (see tools/pins.json for the pinned commits):
    X3D_MCP     a checkout of the validator fork
    LOOM_GATE   the folder that holds loom_gate.py and validate_fork.py (gobbler-demiurge/tools in the Loom repository)
The Python that runs this needs lxml and xmlschema (the fork's own requirements).

DIR/expect.json may hold {"file.x3d": {"must_fail": ["rule-id", ...]}} for fixtures that are red on purpose. For those files the witness is green only if every named rule fires;
a fixture that comes out clean means the witness is blind, and that is a failure. Exit 1 on any unexpected finding or any blind fixture.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import loomsong_rules                                              # noqa: E402


def gate(path, gate_dir, fork):
    env = dict(os.environ, X3D_MCP=fork)
    r = subprocess.run([sys.executable, "-I", os.path.join(gate_dir, "loom_gate.py"), path, "--json", "--fork"], capture_output=True, text=True, env=env, timeout=300)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return [{"rule": "gate-crash", "severity": "error", "line": 0, "message": (r.stderr or r.stdout)[-400:]}]


def main(argv):
    a = [x for x in argv if not x.startswith("--")]
    out = argv[argv.index("--out") + 1] if "--out" in argv else None
    if out and out in a:
        a.remove(out)
    d = a[0]
    gate_dir, fork = os.environ.get("LOOM_GATE"), os.environ.get("X3D_MCP")
    if not gate_dir or not fork:
        sys.exit("set LOOM_GATE and X3D_MCP (see tools/pins.json)")
    expect = json.load(open(os.path.join(d, "expect.json"))) if os.path.exists(os.path.join(d, "expect.json")) else {}
    report, bad = {"folder": d, "files": {}}, 0
    for name in sorted(os.listdir(d)):
        if not name.endswith(".x3d"):
            continue
        p = os.path.join(d, name)
        fs = [f for f in gate(p, gate_dir, fork) if f.get("severity") in ("error", "warning")]
        fs += [dict(f, source="loomsong") for f in loomsong_rules.check(open(p, encoding="utf-8").read())]
        errors = [f for f in fs if f["severity"] == "error"]
        must = expect.get(name, {}).get("must_fail")
        if must is None:
            ok = not errors
            note = "clean" if ok else "; ".join("%s (line %s)" % (f["rule"], f.get("line")) for f in errors)[:300]
        else:
            fired = {f["rule"] for f in errors}
            missing = [r for r in must if r not in fired]
            ok = not missing
            note = "red on purpose: %s fired" % ", ".join(sorted(fired)) if ok else "BLIND: %s did not fire" % ", ".join(missing)
        warnings = [f["rule"] for f in fs if f["severity"] == "warning"]
        report["files"][name] = {"ok": ok, "note": note, "errors": len(errors), "warnings": warnings, "expected_red": must is not None}
        bad += 0 if ok else 1
        counts = {}
        for w in warnings:
            counts[w] = counts.get(w, 0) + 1
        print("%s %-26s %s%s" % ("PASS" if ok else "FAIL", name, note, ("  [warnings: %s]" % ", ".join("%d x %s" % (n, w) for w, n in sorted(counts.items()))) if warnings else ""))
    report["failed"] = bad
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        json.dump(report, open(out, "w"), indent=1)
    print("%d files, %d failed" % (len(report["files"]), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
