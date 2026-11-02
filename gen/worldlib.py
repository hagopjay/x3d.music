"""Shared pieces of the two world generators (P3): the score card as a clock and a bar grid, 24-bit event textures, shader assembly, directed-camera tracks and the document builder.

Conventions every world follows (spec: Scene architecture, Camera):
  * time is seconds on the performance clock, D = card seconds + the master's ring-out tail (audio/render.py TAILS); the page sets FractionBus = t / D and everything else follows from that;
  * a note's visual life is a row of an event texture (EventTable: a header per row, then four texels per event, [t_on], [t_off], [velocity, aux, kind], [note id]), times and ids as 24-bit
    fixed point in R, G, B with A always 255 (a time resolves to about 14 microseconds at D = 230 s; the spec's 16 bits would be 3.5 ms, too coarse for the Sync witness's 0.99, and the id is the
    card's note index so an id-colour render can name the note). The texture is NEAREST, no mipmaps;
  * every shader declares u_time, u_dur, u_idpass and u_calm and gets u_time by ROUTE from SecondsBus (trap rule bus-wired);
  * shot lists are data: cuts land only on phrase downbeats, a move lasts a whole number of bars, and cut pace follows the composer note density (camera grammar 1 to 3).
"""
import json, math, os, re, sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (HERE, os.path.join(ROOT, "score")):
    if p not in sys.path:
        sys.path.insert(0, p)
from cardlib import TempoMap                                                   # noqa: E402
from x3dw import N, Node, document, mf, num, route, shader, time_bus           # noqa: E402
import meshlib as M                                                            # noqa: E402

TAILS = {"turca": 6.0, "ode": 9.0}          # seconds of ring-out after the last note; must equal audio/render.py TAILS (a test checks)
SHADER_DIR = os.path.join(HERE, "shaders")
OUT = os.path.join(ROOT, "build", "worlds")
CUT_EPS = 1.0 / 120.0                       # a cut is two interpolator keys this far apart (shorter than any frame at 60 Hz)
T24 = 16777215.0


# ---- the score card as a clock ------------------------------------------------------------------
class Card:
    """A loomsong.score/1 card with the clock functions the generators need: quarters to seconds, the bar grid, the form passes."""

    def __init__(self, piece):
        self.piece = piece
        with open(os.path.join(ROOT, "score", piece + ".score.json"), encoding="utf-8") as f:
            self.c = json.load(f)
        c = self.c
        self.notes, self.form, self.harmony, self.key_map = c["notes"], c["form"], c["harmony"], c["key_map"]
        self.tm = TempoMap([(Fr(e["q"]), Fr(e["qpm"])) for e in c["tempo_map"]])
        self.beats = int(c["meter"].split("/")[0])
        first = c["tempo_map"][0]
        self.pickup = (self.beats - (int(first["beat"]) - 1)) % self.beats if first["bar"] == 0 else 0
        self.seconds = c["checks"]["seconds"]
        self.D = round(self.seconds + TAILS[piece], 3)
        self.total_q = Fr(c["checks"]["quarters_performed"])
        self.passes = [dict(i=i, id=f["id"], rep=f["rep"], q0=Fr(f["q0"]), q1=Fr(f["q1"]), t0=f["t0"], t1=f["t1"], label=f["label"], bars=f["bars"]) for i, f in enumerate(self.form)]

    def q_t(self, q):
        return float(self.tm.seconds(Fr(q)))

    def t_q(self, t):
        return float(self.tm.quarters(Fr(t).limit_denominator(10 ** 7)))

    def bar_q(self, b):
        """Quarter position of the downbeat of performed bar b (b >= 1)."""
        return Fr((b - 1) * self.beats) + self.pickup

    def pass_of(self, q):
        for p in self.passes:
            if p["q0"] <= q < p["q1"]:
                return p
        return self.passes[-1]

    def downbeats(self):
        """Every performed full bar: dicts {bar, q, t, pass}. The upbeat (bar 0) is not a downbeat."""
        out, b = [], 1
        while self.bar_q(b) < self.total_q:
            q = self.bar_q(b)
            out.append(dict(bar=b, q=q, t=self.q_t(q), pass_i=self.pass_of(q)["i"]))
            b += 1
        return out

    def composer(self):
        return [n for n in self.notes if n["layer"] == "composer"]

    def onsets_per_second(self, t0, t1):
        """Composer note onsets (grace notes not counted) per second in [t0, t1)."""
        k = sum(1 for n in self.notes if n["layer"] == "composer" and not n.get("g") and t0 <= n["t"] < t1)
        return k / max(t1 - t0, 1e-9)


# ---- event textures -----------------------------------------------------------------------------
def b24(t, D):
    """t seconds as a 24-bit integer of t / D, clipped to 0 .. 2^24 - 1."""
    return max(0, min(16777215, int(round(t / D * T24))))


def texel(r, g, b, a=255):
    return "0x%02X%02X%02X%02X" % (r, g, b, a)


def texel24(v, a=255):
    return texel(v >> 16, (v >> 8) & 255, v & 255, a)


def from24(v, D):
    return v / T24 * D


def tex_props():
    return N("TextureProperties", containerField="textureProperties", generateMipMaps=False, magnificationFilter="NEAREST_PIXEL", minificationFilter="NEAREST_PIXEL",
             boundaryModeS="CLAMP_TO_EDGE", boundaryModeT="CLAMP_TO_EDGE")


class EventTable:
    """Rows of events as one PixelTexture, laid out as a single texel stream wrapped at 1024 texels per line (shader function tx()).
    Texel 0 is B, the stream index where the events begin. Row r has a header at texels 1 + 2r (index of its first event) and 2 + 2r (its event count), both 24-bit.
    An event is four texels at B + 4 * (first + i): [t_on], [t_off], [velocity, aux, kind], [note id]. Events inside a row are sorted by t_on, which is what the shader's binary search needs.
    An event is (t_on, t_off, vel, aux, kind, id): seconds, seconds, three bytes (0..255) the shader may read, and the card's note index."""
    PER = 4
    WIDTH = 1024

    def __init__(self, name, rows, D):
        self.name, self.D = name, D
        self.rows = [sorted(r, key=lambda e: (e[0], e[1], e[5])) for r in rows]
        self.n_events = sum(len(r) for r in self.rows)
        self.max_events = max((len(r) for r in self.rows), default=0)
        self.base = 1 + 2 * len(self.rows)
        total = self.base + self.PER * self.n_events
        self.height = max(1, -(-total // self.WIDTH))
        assert self.height <= 8192 and self.base < (1 << 24), (name, self.height)
        self._used = False

    @property
    def width(self):
        return self.WIDTH

    def texels(self):
        out = [texel24(self.base)]
        first = 0
        for r in self.rows:
            out += [texel24(first), texel24(len(r))]
            first += len(r)
        for r in self.rows:
            for on, off, vel, aux, kind, nid in r:
                out += [texel24(b24(on, self.D)), texel24(b24(off, self.D)), texel(int(vel), int(aux), int(kind)), texel24(int(nid))]
        out += [texel(0, 0, 0)] * (self.WIDTH * self.height - len(out))
        return out

    def node(self):
        """The PixelTexture the first time, a USE of it afterwards (a table is shared by every shader that reads it)."""
        if self._used:
            return N("PixelTexture", USE="Tex_" + self.name)
        self._used = True
        return N("PixelTexture", tex_props(), DEF="Tex_" + self.name, image="%d %d 4 %s" % (self.WIDTH, self.height, " ".join(self.texels())), repeatS=False, repeatT=False)

    def field(self):
        return ("u_" + self.name, "SFNode", "inputOutput", self.node())

    def decode(self, row, texels=None):
        """Read a row back out of the texel text, the way the shader does. Returns [(t_on, t_off, vel, aux, kind, id)]."""
        tx = [int(s, 16) for s in (texels or self.texels())]
        v24 = lambda i: (tx[i] >> 8) & 0xFFFFFF
        base, first, n = v24(0), v24(1 + 2 * row), v24(2 + 2 * row)
        out = []
        for i in range(n):
            k = base + self.PER * (first + i)
            a, b, c, d = tx[k:k + 4]
            out.append((from24(v24(k), self.D), from24(v24(k + 1), self.D), (c >> 24) & 255, (c >> 16) & 255, (c >> 8) & 255, v24(k + 3)))
        return out

    def texture_bytes(self):
        return self.WIDTH * self.height * 4


# ---- shaders ------------------------------------------------------------------------------------
_HEADER = "#version 300 es\nprecision highp float;\nprecision highp int;\nprecision highp sampler2D;\n"


def glsl(name, seen=None):
    """Read gen/shaders/<name>.glsl, expand `//@include other` lines, strip comments and blank lines (the world file carries every shader as text)."""
    seen = seen or set()
    if name in seen:
        return ""
    seen.add(name)
    out = []
    with open(os.path.join(SHADER_DIR, name + ".glsl"), encoding="utf-8") as f:
        for line in f.read().splitlines():
            m = re.match(r"\s*//@include\s+(\w+)", line)
            if m:
                out.append(glsl(m.group(1), seen))
                continue
            line = re.sub(r"//.*$", "", line).rstrip()
            if line.strip():
                out.append(line)
    return "\n".join(out) + "\n"


def stage(name):
    """A full shader source: the version line, default precisions, then the file with its includes."""
    return _HEADER + glsl(name)


class Shaders:
    """Makes ComposedShaders with the four standard fields and remembers their names so the ROUTEs from SecondsBus can be written at the end."""

    def __init__(self, D):
        self.D, self.names = D, []

    def make(self, def_, vs, fs, extra=()):
        assert def_ not in self.names, def_
        fields = [("u_time", "SFFloat", "inputOutput", 0), ("u_dur", "SFFloat", "inputOutput", self.D), ("u_idpass", "SFFloat", "inputOutput", 0), ("u_calm", "SFFloat", "inputOutput", 0)]
        self.names.append(def_)
        return shader(def_, fields + list(extra), stage(vs), stage(fs))

    def routes(self):
        return [route("SecondsBus", "value_changed", n, "u_time") for n in self.names]


# ---- interpolators and the directed camera -------------------------------------------------------
def keys_of(times, D):
    """Strictly increasing key fractions in 0..1 from times in seconds (equal neighbours are pushed apart by one unit in the last decimal)."""
    ks, last = [], -1.0
    for t in times:
        k = round(min(max(t / D, 0.0), 1.0), 7)
        if k <= last:
            k = round(last + 1e-7, 7)
        ks.append(k)
        last = k
    assert ks[-1] <= 1.0 + 1e-9, "key past the end"
    return ks


def interpolator(kind, def_, times, values, D, places=4):
    """A ScalarInterpolator / PositionInterpolator / OrientationInterpolator / ColorInterpolator whose keys are fractions of the whole piece."""
    assert len(times) == len(values) and len(times) >= 1
    ks = keys_of(times, D)
    flat = []
    for v in values:
        flat += list(v) if isinstance(v, (tuple, list)) else [v]
    return N(kind, DEF=def_, key=mf(ks, 7), keyValue=mf(flat, places))


def smooth(s):
    return s * s * (3.0 - 2.0 * s)


class Shot:
    """A camera shot: [t0, t1) seconds, eye and target either fixed points or functions of s in 0..1 (eased progress along the shot)."""
    __slots__ = ("name", "t0", "t1", "eye", "tgt", "fov", "up", "ease")

    def __init__(self, name, t0, t1, eye, tgt, fov=None, up=(0.0, 1.0, 0.0), ease=True):
        self.name, self.t0, self.t1, self.eye, self.tgt, self.fov, self.up, self.ease = name, t0, t1, eye, tgt, fov, up, ease

    def at(self, s):
        e = smooth(s) if self.ease else s
        f = lambda p: tuple(p(e)) if callable(p) else tuple(p)
        return f(self.eye), f(self.tgt)

    @property
    def moving(self):
        return callable(self.eye) or callable(self.tgt)


def camera_nodes(shots, D, fov=0.95, def_="Cam", step=0.25):
    """(Viewpoint, [interpolators], [routes]) for a shot list. A cut is two keys CUT_EPS apart; a static shot holds with two equal keys; a move is sampled every `step` seconds
    (more than eight keys per turn of any orbit, which the shortest-arc OrientationInterpolator needs)."""
    times, pos, rot, fovs = [], [], [], []
    for sh in shots:
        end = sh.t1 - CUT_EPS
        n = max(2, int(math.ceil((sh.t1 - sh.t0) / step)) + 1) if sh.moving else 2
        for k in range(n):
            s = k / (n - 1)
            t = sh.t0 + (end - sh.t0) * s
            eye, tgt = sh.at(s)
            times.append(t)
            pos.append(eye)
            rot.append(M.look_rotation(eye, tgt, sh.up))
            fovs.append(sh.fov if sh.fov is not None else fov)
    vp = N("Viewpoint", DEF=def_, position=mf(pos[0], 4), orientation=mf(rot[0], 5), fieldOfView=num(fovs[0], 4), description="", centerOfRotation=mf(shots[0].tgt if not callable(shots[0].tgt) else shots[0].tgt(0.0), 3))
    ints = [interpolator("PositionInterpolator", def_ + "Pos", times, pos, D, 3), interpolator("OrientationInterpolator", def_ + "Rot", times, rot, D, 5)]
    rts = [route("FractionBus", "value_changed", def_ + "Pos", "set_fraction"), route(def_ + "Pos", "value_changed", def_, "position"),
           route("FractionBus", "value_changed", def_ + "Rot", "set_fraction"), route(def_ + "Rot", "value_changed", def_, "orientation")]
    if len(set(fovs)) > 1:
        ints.append(interpolator("ScalarInterpolator", def_ + "Fov", times, fovs, D, 4))
        rts += [route("FractionBus", "value_changed", def_ + "Fov", "set_fraction"), route(def_ + "Fov", "value_changed", def_, "fieldOfView")]
    return vp, ints, rts


def shot_blocks(card, phrase_bars=4, dense=6.0):
    """Cut points for the shot list, as [(t0, t1, pass_index, bars)]. Cuts land on phrase downbeats only (every `phrase_bars` bars counted from the first downbeat of a form pass, and the
    section change itself); a passage whose composer note rate is under `dense` per second holds two phrases per shot. The final block runs to the end of the piece (the ring-out tail)."""
    db = card.downbeats()
    by_pass = {}
    for d in db:
        by_pass.setdefault(d["pass_i"], []).append(d)
    cuts = []                                                    # (t, pass_i, bars_to_next)
    for pi in sorted(by_pass):
        ds = by_pass[pi]
        if len(ds) < 2:
            continue
        idx = list(range(0, len(ds), phrase_bars))
        if len(idx) > 1 and len(ds) - idx[-1] < max(2, phrase_bars // 2):
            idx.pop()                                            # a stub of one or two bars joins the previous phrase
        for i in idx:
            cuts.append((ds[i]["t"], pi, ds[i]["bar"]))
    cuts[0] = (0.0, cuts[0][1], cuts[0][2])
    ends = [c[0] for c in cuts[1:]] + [card.D]
    blocks = []
    for (t0, pi, b0), t1 in zip(cuts, ends):
        blocks.append(dict(t0=t0, t1=t1, pass_i=pi, bar0=b0, rate=card.onsets_per_second(t0, t1)))
    out, i = [], 0
    while i < len(blocks):                                       # sparse neighbours inside one pass merge into one longer shot
        b = blocks[i]
        if b["rate"] < dense and i + 1 < len(blocks) and blocks[i + 1]["pass_i"] == b["pass_i"] and blocks[i + 1]["rate"] < dense:
            b = dict(b, t1=blocks[i + 1]["t1"])
            i += 1
        out.append(b)
        i += 1
    return out


# ---- the document -------------------------------------------------------------------------------
class World:
    """Collects scene children, interpolators and ROUTEs for one piece, counts the budgets, and writes the document (ROUTEs last, after the nodes they name)."""

    def __init__(self, card):
        self.card, self.D = card, card.D
        self.head, self.nodes, self.routes = [], [], []
        self.sh = Shaders(self.D)
        self._shared = set()
        self.stats = dict(shapes=0, triangles=0, texture_bytes=0, interpolator_keys=0, transforms=0, tables={})
        self.components = [("Interpolation", 2), ("Navigation", 3), ("Shaders", 1), ("Shape", 1), ("Texturing", 2), ("Time", 1)]

    def add(self, *nodes):
        self.nodes += [n for n in nodes if n is not None]

    def shared(self, name, make):
        """A ComposedShader several Shapes use: the full node the first time, a USE of it afterwards (one copy of the source in the file, one ROUTE from SecondsBus)."""
        if name in self._shared:
            return N("ComposedShader", USE=name)
        self._shared.add(name)
        return make()

    def table(self, t):
        self.stats["texture_bytes"] += t.texture_bytes()
        self.stats["tables"][t.name] = dict(rows=len(t.rows), width=t.width, max_events=t.max_events)
        return t

    def shape(self, mesh, sh, blend=False, solid=True, normals=True, color=True, attrs=True, name=None):
        """A Shape for a mesh and a ComposedShader. blend=True adds Material transparency (X_ITE blends a shape's alpha only when its appearance says it is transparent; probe B)."""
        app = N("Appearance", *([N("Material", transparency="0.001")] if blend else []), sh)
        self.stats["shapes"] += 1
        self.stats["triangles"] += int(mesh.triangles)
        return N("Shape", app, M.geometry(mesh, normals=normals, color=color, attrs=attrs, solid=solid), DEF=name)

    def drive(self, bus, def_, field_to, times, values, kind, node_def=None, places=4):
        """An interpolator named `def_` (keys in fractions of D) routed from `bus` to `node.field`."""
        it = interpolator(kind, def_, times, values, self.D, places)
        self.stats["interpolator_keys"] += len(times)
        self.add(it)
        self.routes += [route(bus, "value_changed", def_, "set_fraction"), route(def_, "value_changed", *field_to)]
        return it

    def xml(self, title, description, background=(0.0, 0.0, 0.0)):
        head = [N("NavigationInfo", type='"NONE"', headlight=False), N("Background", skyColor=mf(background, 3))]
        bus = time_bus(self.D) + [N("TimeSensor", DEF="Clock", cycleInterval=num(self.D, 3), loop=True, enabled=False)]
        kids = self.head + head + bus + self.nodes
        routes = [route("Clock", "fraction_changed", "FractionBus", "set_fraction")] + self.routes + self.sh.routes()
        return document(kids + routes, components=self.components, title=title, description=description, generator="loomsong gen/world_%s.py" % self.card.piece)


def write_world(world, title, description, extra=None, background=(0.0, 0.0, 0.0), out=None):
    """Write <out>/<piece>.x3d and <piece>.report.json (out defaults to build/worlds); returns the report."""
    out = out or OUT
    os.makedirs(out, exist_ok=True)
    text = world.xml(title, description, background)
    path = os.path.join(out, world.card.piece + ".x3d")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    st = dict(world.stats)
    st.update(piece=world.card.piece, D=world.D, bytes=len(text.encode("utf-8")), draw_calls=st["shapes"], shaders=len(world.sh.names))
    if extra:
        st.update(extra)
    with open(os.path.join(out, world.card.piece + ".report.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(st, indent=1, sort_keys=True) + "\n")
    return st


# ---- small helpers both worlds use ---------------------------------------------------------------
TAU = 2 * math.pi
X_AXIS, Y_AXIS, Z_AXIS = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)


def lin(r, g, b):
    """sRGB bytes to linear light (the shaders work in linear light)."""
    return tuple((c / 255.0) ** 2.2 for c in (r, g, b))


def vec(*v):
    return " ".join(num(x, 4) for x in v)


def lerp3(a, b, s):
    return tuple(a[i] + (b[i] - a[i]) * s for i in range(3))


def orbit(c, r, y, a0, a1):
    """A function of s in 0..1: a point circling c at radius r and height y from angle a0 to a1 (0 is +Z)."""
    return lambda s: (c[0] + r * math.sin(a0 + (a1 - a0) * s), y, c[2] + r * math.cos(a0 + (a1 - a0) * s))
