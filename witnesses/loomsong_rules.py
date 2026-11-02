#!/usr/bin/env python3
"""The five Loomsong trap rules. Stdlib only; one pass over the file, findings carry line numbers.

    python3 -I witnesses/loomsong_rules.py FILE.x3d [...] [--json]

They sit beside the Loom's own gate (`loom_gate.py`, eleven rules, pinned in tools/pins.json) and run with it in CI. They live here until they go to the gate's own repository
by pull request; each has one passing and one failing test in test_loomsong_rules.py.

  bus-wired            every ComposedShader (a definition, not a USE) is DEF'd, declares a field u_time, and receives a ROUTE from SecondsBus.value_changed
  data-texture-nearest a texture node used as shader data (inside a ComposedShader field) has TextureProperties with NEAREST_PIXEL magnification and minification and no mipmaps
  splat-bbox           every GaussianSplats node (a definition) has bboxSize and bboxCenter
  movie-not-still      a MovieTexture url never ends in .png, .jpg or .jpeg
  version-fits-nodes   a file that uses GaussianSplats declares version 4.1
"""
import json, re, sys
import xml.parsers.expat

RULES = ("bus-wired", "data-texture-nearest", "splat-bbox", "movie-not-still", "version-fits-nodes")
TEXTURES = ("PixelTexture", "ImageTexture", "MovieTexture")


class El:
    __slots__ = ("tag", "attrs", "kids", "line", "parent")

    def __init__(self, tag, attrs, line, parent):
        self.tag, self.attrs, self.kids, self.line, self.parent = tag, attrs, [], line, parent

    def walk(self):
        yield self
        for k in self.kids:
            yield from k.walk()


def parse(text):
    p = xml.parsers.expat.ParserCreate()
    root, cur = [None], [None]

    def start(tag, attrs):
        e = El(tag, dict(attrs), p.CurrentLineNumber, cur[0])
        if cur[0] is None:
            root[0] = e
        else:
            cur[0].kids.append(e)
        cur[0] = e

    def end(tag):
        cur[0] = cur[0].parent

    p.StartElementHandler, p.EndElementHandler = start, end
    p.Parse(text.encode("utf-8") if isinstance(text, str) else text, True)
    return root[0]


def F(rule, el, msg):
    return {"rule": rule, "severity": "error", "line": el.line, "message": msg}


def check(text):
    root = parse(text)
    els = list(root.walk())
    defs = {e.attrs["DEF"]: e for e in els if "DEF" in e.attrs}
    routes = [(e.attrs.get("fromNode"), e.attrs.get("fromField"), e.attrs.get("toNode"), e.attrs.get("toField")) for e in els if e.tag == "ROUTE"]
    out = []

    # bus-wired
    for e in els:
        if e.tag != "ComposedShader" or "USE" in e.attrs:
            continue
        name = e.attrs.get("DEF")
        if not any(k.tag == "field" and k.attrs.get("name") == "u_time" for k in e.kids):
            out.append(F("bus-wired", e, "ComposedShader %s declares no field u_time" % (name or "(no DEF)")))
        if not name:
            out.append(F("bus-wired", e, "ComposedShader has no DEF, so no ROUTE can reach it: DEF it and route SecondsBus.value_changed to its u_time"))
        elif ("SecondsBus", "value_changed", name, "u_time") not in routes:
            out.append(F("bus-wired", e, "no ROUTE from SecondsBus.value_changed to %s.u_time" % name))

    # data-texture-nearest
    def data_textures():
        for e in els:
            if e.tag in TEXTURES or ("USE" in e.attrs and defs.get(e.attrs["USE"]) is not None and defs[e.attrs["USE"]].tag in TEXTURES):
                p = e.parent
                if p is not None and p.tag == "field" and p.parent is not None and p.parent.tag == "ComposedShader":
                    yield e, (defs[e.attrs["USE"]] if "USE" in e.attrs else e)
    for use, tex in data_textures():
        tp = next((k for k in tex.kids if k.tag == "TextureProperties"), None)
        if tp is None:
            out.append(F("data-texture-nearest", use, "%s used as shader data has no TextureProperties: add NEAREST_PIXEL filters and generateMipMaps='false'" % tex.tag))
            continue
        for a in ("magnificationFilter", "minificationFilter"):
            if tp.attrs.get(a) != "NEAREST_PIXEL":
                out.append(F("data-texture-nearest", tp, "%s is %s: a data texture needs NEAREST_PIXEL" % (a, tp.attrs.get(a, "unset (default filtering blends neighbouring texels)"))))
        if tp.attrs.get("generateMipMaps", "").lower() != "false":
            out.append(F("data-texture-nearest", tp, "generateMipMaps is %s: a data texture needs it explicitly 'false'" % tp.attrs.get("generateMipMaps", "unset")))

    # splat-bbox
    for e in els:
        if e.tag == "GaussianSplats" and "USE" not in e.attrs:
            for a in ("bboxSize", "bboxCenter"):
                if a not in e.attrs:
                    out.append(F("splat-bbox", e, "GaussianSplats %s has no %s: the browser cannot cull or sort it without a box" % (e.attrs.get("DEF", ""), a)))

    # movie-not-still
    for e in els:
        if e.tag == "MovieTexture" and "USE" not in e.attrs:
            u = e.attrs.get("url", "")
            urls = re.findall(r'"([^"]*)"', u) or ([u] if u.strip() else [])
            for x in urls:
                if re.search(r"\.(png|jpe?g)$", re.split(r"[?#]", x.strip())[0], re.I):
                    out.append(F("movie-not-still", e, "MovieTexture url %s is a still image: use ImageTexture, or a real movie" % x))

    # version-fits-nodes
    spl = next((e for e in els if e.tag == "GaussianSplats"), None)
    if spl is not None and root.attrs.get("version") != "4.1":
        out.append(F("version-fits-nodes", root, "file uses GaussianSplats (line %d) but declares version %s: GaussianSplats exists only in X3D 4.1" % (spl.line, root.attrs.get("version", "(none)"))))
    return out


def main(argv):
    as_json = "--json" in argv
    files = [a for a in argv if not a.startswith("--")]
    allf, bad = [], 0
    for f in files:
        try:
            fs = check(open(f, encoding="utf-8").read())
        except xml.parsers.expat.ExpatError as e:
            fs = [{"rule": "parse", "severity": "error", "line": getattr(e, "lineno", 0), "message": "not well-formed: %s" % e}]
        for x in fs:
            x["file"] = f
        allf += fs
        bad += len(fs)
        if not as_json:
            for x in fs:
                print("%s:%d: error %s %s" % (f, x["line"], x["rule"], x["message"]))
    if as_json:
        print(json.dumps({"files": len(files), "findings": allf}, indent=1))
    else:
        print("%d files: %d errors" % (len(files), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
