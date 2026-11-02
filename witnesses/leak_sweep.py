#!/usr/bin/env python3
"""Leak sweep, the first half of the Truth witness.

Scans a tree (the repo, or a built page) for things that must never reach a public place:
keys, cloud paths, private links, AI model or vendor names, and costs. Exit code 1 on any hit.

    python3 -I witnesses/leak_sweep.py [--root DIR] [--json] [--private FILE]

--private FILE (or env LOOM_SWEEP_PRIVATE) names a file kept outside the repo with one literal
string per line (a cloud project id, a run-as identity, a bucket name): any line of any scanned
file containing one of them, in any case, is a hit. The strings are never printed back.

A line may carry the marker  sweep:allow  (all rules) or  sweep:allow RULE  to be skipped.
Words are built from fragments below so this file does not trip its own sweep.
"""
import argparse, json, os, re, sys

W = lambda *p: "".join(p)

TEXT_EXT = {".md", ".txt", ".json", ".jsonl", ".py", ".js", ".mjs", ".html", ".css", ".x3d", ".glsl", ".yml", ".yaml",
            ".toml", ".sh", ".cfg", ".ini", ".tpl", ".frag", ".vert", ".xml", ".svg", ".csv", ".krn", ".musicxml"}
PROSE_EXT = {".md", ".html", ".txt", ".json", ".jsonl", ".x3d", ".xml", ".tpl"}      # where a dollar figure is a cost, not a shell variable
SKIP_DIRS = {".git", "node_modules", "build", "__pycache__", ".venv", "venv"}

RULES = [
    ("key-api",       re.compile(W(r"AIza[0-9A-Za-z_\-]{35}", r"|\bsk-[A-Za-z0-9_\-]{20,}", r"|\bgh[pousr]_[A-Za-z0-9]{30,}", r"|\bAKIA[0-9A-Z]{16}\b", r"|\bhf_[A-Za-z0-9]{30,}"))),
    ("key-private",   re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer-token",  re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{24,}")),
    ("service-acct",  re.compile(r"[A-Za-z0-9\-]+@[A-Za-z0-9\-]+\.iam\.gserviceaccount\.com")),
    ("private-link",  re.compile(W(r"clau", r"de\.ai/(artifact|code|project|chat|share)", r"|(drive|docs)\.goo", r"gle\.com", r"|\bgs://", r"|storage\.goo", r"gleapis\.com"))),
    ("vendor-name",   re.compile(W(r"(?i)\b(", "gem", "ini|", "clau", "de|", "anthro", "pic|", "son", "net|", "hai", "ku|", "open", "ai|", "chat", "gpt|", "deep", "mind|",
                                  "ver", "tex[ \\-]?", "a", "i|", "ly", "ria|", "ve", "o ?3|", "ima", "gen|", "bar", "d|", "nvi", "dia|", "goo", "gle)\\b"))),
    ("cost",          re.compile(r"(?<![\w$])\$\s?\d[\d,]*(\.\d+)?\b")),
]
ALLOW = re.compile(r"sweep:allow(?:\s+([a-z\-]+))?")

# Image metadata is where a vendor's name, a camera, a content-credentials block or a prompt hides, so a picture in the repository may hold its pixels and one line of our own: a comment that starts "AI-made"
# (or "Test pattern", the label of a stand-in made by code that is not AI-made).
# The structure is read (chunks of a PNG, segments of a JPEG), not searched for words: compressed pixels hold any four bytes by chance.
IMAGE_EXT = {".png", ".jpg", ".jpeg"}
IMAGE_LABEL = (b"AI-made", b"Test pattern")
PNG_SIG = b"\x89PNG\r\n\x1a\n"
PNG_PLAIN = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND"}
JPEG_PLAIN = {0xC0, 0xC1, 0xC2, 0xC4, 0xDB, 0xDD, 0xDA}           # frame headers, tables, restart interval, scan


def scan_image(rel, data):
    """Hits for one PNG or JPEG: anything in it that is not pixels or our own label."""
    def hit(why):
        return {"file": rel, "line": 0, "rule": "image-metadata", "why": why}
    if data.startswith(PNG_SIG):
        pos, seen_end = 8, False
        while pos + 8 <= len(data):
            n, t = int.from_bytes(data[pos:pos + 4], "big"), data[pos + 4:pos + 8]
            body = data[pos + 8:pos + 8 + n]
            if t == b"tEXt":
                if not body.partition(b"\0")[2].startswith(IMAGE_LABEL):
                    return [hit("png text chunk that is not our label")]
            elif t not in PNG_PLAIN:
                return [hit("png chunk " + t.decode("latin-1"))]
            pos += 12 + n
            if t == b"IEND":
                seen_end = True
                break
        if not seen_end:
            return [hit("png without IEND")]
        return [hit("bytes after the png's end")] if pos != len(data) else []
    if data[:2] == b"\xff\xd8":
        pos = 2
        while pos + 4 <= len(data) and data[pos] == 0xFF:
            m = data[pos + 1]
            n = int.from_bytes(data[pos + 2:pos + 4], "big")
            body = data[pos + 4:pos + 2 + n]
            if m == 0xFE:
                if not body.startswith(IMAGE_LABEL):
                    return [hit("jpeg comment that is not our label")]
            elif m == 0xE0:
                if not body.startswith(b"JFIF\0"):
                    return [hit("jpeg APP0 that is not JFIF")]
            elif m not in JPEG_PLAIN:
                return [hit("jpeg segment 0xFF%02X" % m)]
            if m == 0xDA:
                break
            pos += 2 + n
        end = data.rfind(b"\xff\xd9")
        if end < 0:
            return [hit("jpeg without EOI")]
        return [hit("bytes after the jpeg's end")] if end + 2 != len(data) else []
    return [hit("not a png or a jpeg by its first bytes")]


def load_private(path):
    if not path or not os.path.isfile(path):
        return []
    out = []
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s.lower())
    return out


def scan_text(rel, text, private):
    ext = os.path.splitext(rel)[1].lower()
    hits = []
    for n, line in enumerate(text.split("\n"), 1):
        allowed = ALLOW.search(line)
        if allowed and not allowed.group(1):
            continue
        for rule, rx in RULES:
            if rule == "cost" and ext not in PROSE_EXT:
                continue
            if allowed and allowed.group(1) == rule:
                continue
            if rx.search(line):
                hits.append({"file": rel, "line": n, "rule": rule})
        low = line.lower()
        for p in private:
            if p in low:
                hits.append({"file": rel, "line": n, "rule": "private-string"})
                break
    return hits


def sweep(root, private_file=None):
    private = load_private(private_file or os.environ.get("LOOM_SWEEP_PRIVATE"))
    hits, scanned = [], 0
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
        for f in sorted(files):
            p = os.path.join(d, f)
            rel = os.path.relpath(p, root)
            ext = os.path.splitext(f)[1].lower()
            if ext in IMAGE_EXT:
                try:
                    data = open(p, "rb").read()
                except OSError:
                    continue
                scanned += 1
                hits += scan_image(rel, data)
                continue
            if ext not in TEXT_EXT and f not in {"LICENSE", "NOTICE", "Makefile", ".gitignore"}:
                # unknown extension: only scan if it looks like text
                try:
                    head = open(p, "rb").read(4096)
                except OSError:
                    continue
                if b"\0" in head:
                    continue
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            scanned += 1
            hits += scan_text(rel, text, private)
    return {"root": os.path.abspath(root), "files_scanned": scanned, "private_strings": len(private), "hits": hits, "clean": not hits}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--private")
    a = ap.parse_args(argv)
    r = sweep(a.root, a.private)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        for h in r["hits"]:
            print("%s:%d: %s%s" % (h["file"], h["line"], h["rule"], (" (" + h["why"] + ")") if h.get("why") else ""))
        print("leak sweep: %d files, %d private strings, %d hits -> %s" % (r["files_scanned"], r["private_strings"], len(r["hits"]), "CLEAN" if r["clean"] else "HITS"))
    return 0 if r["clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
