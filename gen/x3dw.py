"""Small deterministic X3D XML writer shared by every Loomsong generator.

Same inputs give the same bytes: attributes keep insertion order, numbers are formatted by one rule,
the document date comes from SOURCE_DATE_EPOCH (never the clock), and output ends with one newline.
Attributes are single-quoted so MFString values can carry their own double quotes.
"""
import datetime, os

X3D_XSD = {"4.0": "https://www.web3d.org/specifications/x3d-4.0.xsd", "4.1": "https://www.web3d.org/specifications/x3d-4.1.xsd"}


def num(x, places=4):
    """Shortest decimal for x with at most `places` decimals; '-0' becomes '0'."""
    if isinstance(x, int):
        return str(x)
    s = ("%.*f" % (places, x)).rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def mf(values, places=4, per=None):
    """Space-joined MF value. `per` breaks lines after that many numbers (keeps big arrays diffable)."""
    parts = [num(v, places) for v in values]
    if not per:
        return " ".join(parts)
    return "\n      ".join(" ".join(parts[i:i + per]) for i in range(0, len(parts), per))


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;")


class Node:
    __slots__ = ("tag", "attrs", "kids", "cdata")

    def __init__(self, tag, _kids=None, _cdata=None, **attrs):
        self.tag, self.kids, self.cdata = tag, [], _cdata
        self.attrs = {k.rstrip("_").replace("__", ":"): v for k, v in attrs.items() if v is not None}
        for k in _kids or []:
            self.add(k)

    def add(self, *kids):
        for k in kids:
            if k is not None:
                self.kids.append(k)
        return self

    def xml(self, depth=0):
        pad = "  " * depth
        a = "".join(" %s='%s'" % (k, esc(v) if not isinstance(v, bool) else str(v).lower()) for k, v in self.attrs.items())
        if not self.kids and self.cdata is None:
            return "%s<%s%s/>\n" % (pad, self.tag, a)
        out = ["%s<%s%s>" % (pad, self.tag, a)]
        if self.cdata is not None:
            out.append("<![CDATA[%s]]>" % self.cdata)
            out.append("</%s>\n" % self.tag)
            return "".join(out)
        out.append("\n")
        for k in self.kids:
            out.append(k.xml(depth + 1))
        out.append("%s</%s>\n" % (pad, self.tag))
        return "".join(out)


def N(tag, *kids, **attrs):
    return Node(tag, list(kids), None, **attrs)


def iso_date():
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1793491200"))      # 2026-11-01T00:00:00Z unless the build says otherwise
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m-%d")


def document(children, *, version="4.0", profile="Interchange", components=(), title="", description="", generator="loomsong/gen", extra_meta=()):
    head = N("head")
    for name, level in components:
        head.add(N("component", name=name, level=level))
    head.add(N("meta", name="title", content=title), N("meta", name="description", content=description),
             N("meta", name="generator", content=generator), N("meta", name="created", content=iso_date()))
    for k, v in extra_meta:
        head.add(N("meta", name=k, content=v))
    root = Node("X3D", [head, Node("Scene", list(children))], None, profile=profile, version=version,
                xmlns__xsd="http://www.w3.org/2001/XMLSchema-instance", xsd__noNamespaceSchemaLocation=X3D_XSD[version])
    return "<?xml version='1.0' encoding='UTF-8'?>\n" + root.xml()


# ---- shaders ------------------------------------------------------------------------------------
def shader(def_, fields, vs, fs, language="GLSL"):
    """ComposedShader with both parts carrying the data: prefix X_ITE 16.5.1 needs (raw GLSL in CDATA is the shader-raw-source trap).
    fields: [(name, type, accessType, value_or_None_or_Node)]"""
    sh = N("ComposedShader", DEF=def_, language=language)
    for name, typ, access, val in fields:
        f = N("field", name=name, type=typ, accessType=access)
        if isinstance(val, Node):
            f.add(val)
        elif val is not None:
            f.attrs["value"] = val if isinstance(val, str) else num(val)
        sh.add(f)
    sh.add(Node("ShaderPart", [], "data:x-shader/x-vertex," + vs.lstrip("\n"), type="VERTEX"),
           Node("ShaderPart", [], "data:x-shader/x-fragment," + fs.lstrip("\n"), type="FRAGMENT"))
    return sh


def route(frm, ffield, to, tfield):
    return N("ROUTE", fromNode=frm, fromField=ffield, toNode=to, toField=tfield)


def time_bus(duration):
    """FractionBus carries t/D into every interpolator's set_fraction; SecondsBus turns it back into seconds for shaders' u_time.
    The page sets FractionBus.set_fraction each frame; standalone, a TimeSensor Clock feeds it (ROUTEs are written after the nodes they name)."""
    return [N("ScalarInterpolator", DEF="FractionBus", key="0 1", keyValue="0 1"),
            N("ScalarInterpolator", DEF="SecondsBus", key="0 1", keyValue="0 %s" % num(duration, 3)),
            route("FractionBus", "value_changed", "SecondsBus", "set_fraction")]
