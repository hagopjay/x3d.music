#!/usr/bin/env python3
"""World 1, Ode to Joy: the Jacquard tapestry. Writes build/worlds/ode.x3d (+ report and the element map).

Score-true by construction (spec: the weave rule). A gantry loom walks down an 8 by 12 metre tapestry (256 warp threads by 384 weft rows). Each of the four statements of the theme sweeps
rows 0 to 383 over its own duration and lays one print separation of the picture: indigo (statement 1), silver (2), gold (3), ivory with crimson warp accents (4). Row r is woven at the
instant tw = t0 + (r + 0.5) / 384 * (t1 - t0); the cell is owned by one of the notes of that statement's families that is sounding at tw (tables: gen/world_ode.weave_rows), appears
then, glows for as long as its owner sounds and settles. A row with no such note stays bare linen, so busy passages weave dense colour and sparse ones leave the warp showing.
Every note of the card is also a hole in the card chain, a piano roll of 384 cards (one a beat) that runs through the Jacquard head: a hole sounds as it passes the reading bar.
The rose window is the circle of fifths and glows with the pitch classes of the current chord; the shuttle flies for every note of the melody, the batten beats on every kick and snare,
the harness lifts on every hat.

Layout, metres, Y up, the viewer looks toward -Z down a nave 13.4 wide: the tapestry hangs at z = -23.8, the loom stands in front of it, the Jacquard head above at y = 15.2, the rose
window above that, the nave opens toward +Z.
"""
import math, os, sys
from fractions import Fraction as Fr
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import meshlib as M                                                         # noqa: E402
from meshlib import T, S, R, compose, Mesh, merge                           # noqa: E402
import worldlib as W                                                        # noqa: E402
from worldlib import N, mf, num, route, Card, EventTable, Shot, World       # noqa: E402
from worldlib import TAU, X_AXIS, Y_AXIS, Z_AXIS, lin, vec, lerp3, orbit    # noqa: E402,F401
import picture_ode as PIC                                                   # noqa: E402

# ---- layout ---------------------------------------------------------------------------------------
ROWS, COLS = PIC.CH, PIC.CW
TAP_W, TAP_H = 8.0, 12.0
TAP_TOP, TAP_BOT, TAP_Z = 12.8, 0.8, -23.8
WALL_Z = -24.0
HEAD_Y, HEAD_Z = 15.2, -22.9
BELT_Z = -21.95
CARD_P = 0.12                                  # metres of ribbon per beat
HALF_W = 6.7                                   # half the width of the nave between the piers
BAY = 6.5
PIERS = [-21.5 + BAY * k for k in range(9)]
SPRING_Y, CLERE_Y, VAULT_Y = 8.0, 14.0, 21.5
ROSE = (0.0, 20.2, WALL_Z + 0.05)
ROSE_R = 3.1
SHUTTLE_X = 3.85
RAIL_X = 4.75
LANES = ["choir", "strings", "pad", "lead", "brass", "mel", "bass", "timp", "tom", "snare", "kick", "clap", "rim", "clatter", "cymbal", "hat"]     # top to bottom of a card
FAMILY = dict(bass=0, timp=0, pad=1, strings=1, ep=1, lead=2, brass=2, mel=2, choir=3, kick=4, snare=4, tom=4, clap=4, rim=4, clatter=4, cymbal=4, hat=4)
# the five threads and which notes may own a cell of each (the instruments that have joined by that statement)
LAYERS = [dict(name="indigo", sec="S1", insts=("mel",)), dict(name="silver", sec="S2", insts=("mel", "lead")), dict(name="gold", sec="S3", insts=("mel", "brass")),
          dict(name="ivory", sec="S4", insts=("mel", "choir", "pad")), dict(name="crimson", sec="S4", insts=("clap", "rim", "tom", "timp", "snare", "cymbal"))]
MAX_CAND = 6
HIT_Y = 0.55                                   # how far the harness lifts


def pass_times(card):
    return {p["id"]: (p["t0"], p["t1"]) for p in card.passes}


def sweep_vectors(card):
    pt = pass_times(card)
    a = [pt[L["sec"]][0] for L in LAYERS[:4]]
    b = [pt[L["sec"]][1] for L in LAYERS[:4]]
    return a, b


# ---- the weave: which notes own the cells of each row -----------------------------------------------------------------------------
def weave_rows(card):
    """Rows of the weave table, layer * 384 + row: the notes of the layer's families sounding at that row's weave time, at most MAX_CAND (loudest first), as card events."""
    pt = pass_times(card)
    rows = []
    for L in LAYERS:
        t0, t1 = pt[L["sec"]]
        cand = [(i, n) for i, n in enumerate(card.notes) if n["inst"] in L["insts"] and n["t"] < t1 + 1.0 and n["t"] + n["dur"] > t0 - 1.0]
        for r in range(ROWS):
            tw = t0 + (r + 0.5) / ROWS * (t1 - t0)
            on = [(i, n) for i, n in cand if n["t"] <= tw <= n["t"] + n["dur"]]
            on.sort(key=lambda e: (-e[1]["vel"], e[0]))
            on = on[:MAX_CAND]
            rows.append([(n["t"], n["t"] + n["dur"], round(n["vel"] / 127 * 255), FAMILY.get(n["inst"], 0), 0, i) for i, n in on])
    return rows


def owner_hash(x, y):
    """The integer hash the tapestry shader (hash2u) uses to pick a cell's owner among the notes sounding at its row: 32-bit wrap-around arithmetic, identical in GLSL ES 3.00 and in the page."""
    h = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return h ^ (h >> 16)


def cell_owner(rows, layer, col, row):
    """The note index that owns cell (col, row) of the layer: the shader's pick, from the stored (sorted) event row."""
    ids = rows[layer * ROWS + row]
    return ids[owner_hash(col, row) % len(ids)] if ids else None


def weave_time(card, layer, row):
    t0, t1 = pass_times(card)[LAYERS[layer]["sec"]]
    return t0 + (row + 0.5) / ROWS * (t1 - t0)


def chord_rows(card):
    """Rows of the chord table, one per sector of the circle of fifths: the spans of the chords that contain that pitch class (events of kind 1; the id is the chord's index)."""
    rows = [[] for _ in range(12)]
    for k, h in enumerate(card.harmony):
        for pc in h["pcs"]:
            rows[(pc * 7) % 12].append((h["t"], h["t"] + h["dur"], round(min(max(h.get("tension", 0.0), 0.0), 1.0) * 255), 0, 1, k))
    return rows


# ---- buses ------------------------------------------------------------------------------------------------------------------------
def activity_keys(card):
    """Note activity 0..1 once a second: the velocity-weighted onsets in the second around it, scaled so a full band is about 1."""
    ts = np.array([n["t"] for n in card.notes if not n.get("g")])
    vs = np.array([n["vel"] / 127.0 for n in card.notes if not n.get("g")])
    keys = [float(k) for k in range(0, int(card.D) + 1)] + [card.D]
    vals = [float(min(1.0, vs[(ts >= k - 0.5) & (ts < k + 0.5)].sum() / 9.0)) for k in keys]
    sm = [vals[0]] + [0.25 * vals[i - 1] + 0.5 * vals[i] + 0.25 * vals[i + 1] for i in range(1, len(vals) - 1)] + [vals[-1]]
    return keys, sm


def tension_keys(card):
    keys, vals = [0.0], [float(card.harmony[0].get("tension", 0.0))]
    for h in card.harmony[1:]:
        v = float(h.get("tension", 0.0))
        if abs(v - vals[-1]) > 1e-9:
            keys += [max(h["t"] - 0.25, keys[-1] + 0.01), h["t"]]
            vals += [vals[-1], v]
    keys.append(card.D); vals.append(vals[-1])
    return keys, vals


def layer_keys(card):
    keys, vals = [0.0], [0.0]
    for p in card.passes:
        v = {"Intro": 0.0, "S1": 0.0, "S2": 1.0, "S3": 2.0, "S4": 3.0, "Coda": 3.0}[p["id"]]
        if v != vals[-1]:
            keys += [p["t0"] - W.CUT_EPS, p["t0"]]
            vals += [vals[-1], v]
    keys.append(card.D); vals.append(vals[-1])
    return keys, vals


def belt_keys(card):
    """The card chain moves one card (CARD_P metres) a beat: position x = -CARD_P * q(t), keyed on every beat, so it is exact at each beat and within a hundredth of one between."""
    n = int(card.total_q)
    keys = [card.q_t(Fr(b)) for b in range(n + 1)]
    pos = [(-CARD_P * b, HEAD_Y, BELT_Z) for b in range(n + 1)]
    keys.append(card.D); pos.append(pos[-1])
    return keys, pos


def carriage_keys(card):
    """(times, y of the weave line). Parked at the top before statement 1; each statement walks the line from row 0 down to row 383; between statements it is back at the top (the camera
    cuts there); in the coda it climbs out of the way and the whole tapestry shows."""
    pt = pass_times(card)
    times, ys = [0.0], [TAP_TOP]
    for L in LAYERS[:4]:
        t0, t1 = pt[L["sec"]]
        times += [t0, t1 - W.CUT_EPS, t1]
        ys += [TAP_TOP, TAP_BOT, TAP_TOP if L is not LAYERS[3] else TAP_BOT]
    c0 = pt["Coda"][0]
    times += [c0 + 1.5, c0 + 6.5, card.D]
    ys += [TAP_BOT, TAP_TOP, TAP_TOP]
    return monotone(times, ys, 1e-6)


def monotone(times, vals, lo=1e-4):
    out_t, out_v = [], []
    for t, v in zip(times, vals):
        if out_t and t <= out_t[-1] + lo:
            continue
        out_t.append(t); out_v.append(v)
    return out_t, out_v


def hit_keys(times, rest, hit, D, lead=0.06, tail=0.14):
    """Keys for a mechanism that moves from `rest` to `hit` on every event time: lead seconds before, on the event, tail seconds after; crowded ones are thinned, never reordered."""
    ks, vs = [0.0], [rest]
    for i, t in enumerate(times):
        nxt = times[i + 1] if i + 1 < len(times) else D
        for tt, v in ((t - lead, rest), (t, hit), (min(t + tail, (t + nxt - lead) / 2 if nxt - t < lead + tail else t + tail), rest)):
            if tt > ks[-1] + 1e-4 and tt < D:
                ks.append(tt); vs.append(v)
    ks.append(D); vs.append(rest)
    return ks, vs


def shuttle_keys(card):
    """The shuttle flies across the warp for every note of the melody and arrives on the note's onset; it waits at the left end before the theme begins."""
    ons = sorted({n["t"] for n in card.composer()})
    ks, xs = [0.0], [-SHUTTLE_X]
    side = -1
    for i, t in enumerate(ons):
        gap = t - (ons[i - 1] if i else 0.0)
        flight = min(0.30, 0.8 * gap)
        side = -side
        if t - flight > ks[-1] + 1e-4:
            ks.append(t - flight); xs.append(xs[-1])
        if t > ks[-1] + 1e-4:
            ks.append(t); xs.append(side * SHUTTLE_X)
    ks.append(card.D); xs.append(xs[-1])
    return ks, xs


# ---- geometry -----------------------------------------------------------------------------------------
def lanceet_pts(width, spring, c=1.4, n=10):
    """The outline points of a pointed arch opening, left spring to apex to right spring (x from the centre, y from the base): arcs of radius width / 2 + c struck from the opposite side."""
    a = width / 2
    Rr = a + c
    h = math.sqrt(Rr * Rr - c * c)
    th0 = math.atan2(h, -c)                                    # from the left spring's angle at the centre (c, 0) up to the apex
    left = [(c + Rr * math.cos(th), spring + Rr * math.sin(th)) for th in np.linspace(math.pi, th0, n)]
    right = [(-c - Rr * math.cos(th), spring + Rr * math.sin(th)) for th in np.linspace(th0, math.pi, n)]
    return left[:-1] + [(0.0, spring + h)] + right[1:], spring + h


def pointed_slab(width, spring, depth, thickness, top):
    """A slab with a pointed-arch opening up from the base (like an arcade bay): outline CCW, extruded depth along Z, centred on x = 0, base at y = 0."""
    a = width / 2
    outer = a + thickness
    arc, _ = lanceet_pts(width, spring)
    pts = [(-outer, 0.0), (-a, 0.0)] + arc + [(a, 0.0), (outer, 0.0), (outer, top), (-outer, top)]
    return M.extrude_polygon(pts, depth)


def pointed_plate(width, base, spring, depth):
    """A flat pointed-arch shape (a window's glass): from y = base up to the apex."""
    arc, _ = lanceet_pts(width, spring - base)
    pts = [(-width / 2, 0.0), (width / 2, 0.0)] + [(x, y) for x, y in reversed(arc)]
    return M.extrude_polygon(pts, depth).transformed(T(0, base, 0))


def mat(mesh, m, albedo=(1.0, 1.0, 1.0)):
    return mesh.colored(albedo).with_attr("mat", float(m))


STONE, DARK, VAULTC = lin(120, 124, 140), lin(58, 62, 76), lin(40, 44, 62)
BRASS, BRONZE, WOOD, STEEL = lin(196, 150, 78), lin(120, 82, 44), lin(104, 70, 44), lin(150, 158, 172)


def nave_meshes():
    """Everything that never moves: floor, arcades, piers, clerestories with their glass, the vault, the end wall, the loom's rails and the Jacquard head."""
    parts = []
    # floor
    fl = Mesh([(-11, 0, -24), (11, 0, -24), (11, 0, 34), (-11, 0, 34)], [(0, 1, 0)] * 4, [[0, 3, 2], [0, 2, 1]])
    parts.append(mat(fl, 0, (0.3, 0.3, 0.3)))
    bay = pointed_slab(5.2, SPRING_Y, 1.3, 0.65, CLERE_Y)
    clere = pointed_slab(3.4, 3.0, 1.3, 1.55, VAULT_Y - CLERE_Y)
    glass = pointed_plate(3.4, 1.8, 3.0 + 0.0, 0.05)
    for s_ in (-1, 1):
        for k in range(8):
            zb = PIERS[0] + BAY * (k + 0.5)
            m = compose(T(s_ * HALF_W, 0, zb), R(Y_AXIS, math.pi / 2))
            parts.append(mat(bay.transformed(m), 1, STONE))
            parts.append(mat(clere.transformed(compose(T(s_ * HALF_W, CLERE_Y, zb), R(Y_AXIS, math.pi / 2))), 1, STONE))
            parts.append(mat(M.box(1.3, 1.8, 3.4).transformed(T(s_ * HALF_W, CLERE_Y + 0.9, zb)), 1, STONE))                                   # the sill
            parts.append(mat(glass.transformed(compose(T(s_ * (HALF_W - 0.1), CLERE_Y, zb), R(Y_AXIS, -s_ * math.pi / 2))), 6, (0.5, 0.5, 0.5)))
        for z in PIERS:
            x = s_ * (HALF_W - 0.8)
            parts.append(mat(M.cylinder(0.26, 0.26, VAULT_Y, 16).transformed(T(x, 0, z)), 1, STONE))
            parts.append(mat(M.cylinder(0.42, 0.34, 0.5, 16).transformed(T(x, 0, z)), 1, DARK))
            parts.append(mat(M.torus(0.31, 0.07, 16, 6).transformed(T(x, SPRING_Y + 0.5, z)), 1, DARK))
            parts.append(mat(M.torus(0.31, 0.07, 16, 6).transformed(T(x, VAULT_Y - 0.1, z)), 1, DARK))
    # the vault: a pointed barrel from the springing line, ribbed in the shader
    prof, apex = lanceet_pts(2 * HALF_W, VAULT_Y, c=1.4, n=14)
    P_, N_, F_ = [], [], []
    z0, z1, nz = WALL_Z, 34.0, 12
    for j in range(nz + 1):
        z = z0 + (z1 - z0) * j / nz
        for i, (x, y) in enumerate(prof):
            P_.append((x, y, z))
            a, b = prof[max(i - 1, 0)], prof[min(i + 1, len(prof) - 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tx, ty) or 1.0
            N_.append((ty / ln, -tx / ln, 0.0))
    for j in range(nz):
        for i in range(len(prof) - 1):
            a, b = j * len(prof) + i, j * len(prof) + i + 1
            c, d = a + len(prof), b + len(prof)
            F_ += [[a, b, c], [b, d, c]]
    parts.append(mat(Mesh(P_, N_, F_), 2, VAULTC))
    # the end wall behind the tapestry
    ep, _ = lanceet_pts(2 * HALF_W, VAULT_Y, c=1.4, n=14)
    wall = M.extrude_polygon([(-HALF_W, 0.0), (HALF_W, 0.0)] + [(x, y) for x, y in reversed(ep)], 0.6).transformed(T(0, 0, WALL_Z - 0.3))
    parts.append(mat(wall, 10, DARK))
    # the loom's rails, the Jacquard head and its reading bar
    for s_ in (-1, 1):
        parts.append(mat(M.box(0.34, TAP_TOP + 1.8, 0.36).transformed(T(s_ * RAIL_X, (TAP_TOP + 1.8) / 2, -23.35)), 4, BRONZE))
        parts.append(mat(M.box(0.8, 0.5, 0.8).transformed(T(s_ * RAIL_X, 0.25, -23.35)), 4, BRONZE))
        parts.append(mat(M.box(0.6, 0.3, 0.6).transformed(T(s_ * RAIL_X, TAP_TOP + 1.9, -23.35)), 3, BRASS))
    parts.append(mat(M.box(3.0, 2.2, 1.9).transformed(T(0, HEAD_Y, HEAD_Z)), 5, WOOD))
    parts.append(mat(M.box(3.4, 0.3, 2.2).transformed(T(0, HEAD_Y + 1.25, HEAD_Z)), 3, BRASS))
    parts.append(mat(M.box(3.2, 0.22, 2.1).transformed(T(0, HEAD_Y - 1.2, HEAD_Z)), 3, BRASS))
    parts.append(mat(M.cylinder(0.34, 0.34, 3.2, 20).transformed(compose(T(-1.6, HEAD_Y + 0.7, BELT_Z - 0.15), R(Z_AXIS, -math.pi / 2))), 3, BRASS))
    parts.append(mat(M.box(0.07, 2.4, 0.1).transformed(T(0, HEAD_Y, BELT_Z + 0.05)), 9, (1.0, 1.0, 1.0)))
    return merge(parts)


def cords_mesh():
    """Forty-eight thin steel threads from y = 0 to y = 1 across the warp; the carriage scales them to reach the head."""
    xs = np.linspace(-TAP_W / 2 + 0.1, TAP_W / 2 - 0.1, 48)
    return mat(merge([M.box(0.014, 1.0, 0.014).transformed(T(x, 0.5, -22.45)) for x in xs]), 7, STEEL)


def carriage_meshes():
    beam = merge([mat(M.box(9.9, 0.5, 0.62).transformed(T(0, 0.62, -22.85)), 3, BRASS)]
                 + [mat(M.box(0.7, 1.15, 0.95).transformed(T(s_ * RAIL_X, 0.55, -23.05)), 4, BRONZE) for s_ in (-1, 1)]
                 + [mat(M.box(9.2, 0.07, 0.07).transformed(T(0, 0.28, -22.5)), 7, STEEL)])
    batten = mat(M.box(8.4, 0.16, 0.30), 4, BRONZE)
    rods = merge([mat(M.box(0.03, 0.7, 0.03).transformed(T(x, 0.0, 0.0)), 7, STEEL) for x in np.linspace(-3.9, 3.9, 25)])
    body = M.lathe([(0.0, -0.38), (0.07, -0.3), (0.12, -0.1), (0.12, 0.1), (0.07, 0.3), (0.0, 0.38)], 14).transformed(R(Z_AXIS, math.pi / 2))
    bobbin = M.sphere(0.095, 12, 8).transformed(T(0, 0.1, 0.02))
    return beam, batten, rods, mat(body, 3, BRASS), mat(bobbin, 8, (1.0, 1.0, 1.0))


def tapestry_mesh():
    P = [(-TAP_W / 2, TAP_TOP, TAP_Z), (-TAP_W / 2, TAP_BOT, TAP_Z), (TAP_W / 2, TAP_BOT, TAP_Z), (TAP_W / 2, TAP_TOP, TAP_Z)]
    m = Mesh(P, [(0, 0, 1)] * 4, [[0, 1, 2], [0, 2, 3]])
    return m.with_attr("uv", np.array([[0, 0], [0, 1], [1, 1], [1, 0]], float))


def rose_mesh():
    n = 48
    P = [ROSE] + [(ROSE[0] + ROSE_R * math.sin(TAU * i / n), ROSE[1] + ROSE_R * math.cos(TAU * i / n), ROSE[2]) for i in range(n)]
    uv = [(0.0, 0.0)] + [(math.sin(TAU * i / n), math.cos(TAU * i / n)) for i in range(n)]
    F = [[0, 1 + (i + 1) % n, 1 + i] for i in range(n)]
    return Mesh(P, [(0, 0, 1)] * len(P), F).with_attr("uv", np.array(uv))


def shafts_mesh():
    """Slanted translucent quads from the clerestory windows toward the loom and the floor, two crossed per window."""
    parts = []
    for s_ in (-1, 1):
        for k in range(8):
            zb = PIERS[0] + BAY * (k + 0.5)
            top, bot = (s_ * (HALF_W - 0.4), 19.5, zb), (s_ * 1.6, 0.0, zb - 7.5)
            for ax in (0, 1):
                w = 2.2
                d = (0.0, 0.0, w) if ax == 0 else (w * 0.0 + s_ * -w * 0.9, 0.0, 0.0)
                a0, a1 = np.add(top, np.multiply(d, -1)), np.add(top, d)
                b0, b1 = np.add(bot, np.multiply(d, -2.2)), np.add(bot, np.multiply(d, 2.2))
                parts.append(Mesh([a0, a1, b1, b0], [(0, 1, 0)] * 4, [[0, 1, 2], [0, 2, 3]]).with_attr("uv", np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)))
    return merge(parts)


def belt_mesh(card):
    """The card chain as one mesh: a long plate (kind 0) and one hole (kind 1) for every note, where it starts in its beat and as long as it lasts, in the lane of its instrument."""
    n_beats = int(card.total_q)
    L = n_beats * CARD_P
    plate = Mesh([(-0.6, -1.0, 0), (L + 0.6, -1.0, 0), (L + 0.6, 1.0, 0), (-0.6, 1.0, 0)], [(0, 0, 1)] * 4, [[0, 1, 2], [0, 2, 3]])
    plate = plate.with_attr("kind", 0.0).with_attr("loc", np.array([[-0.6, -1.0], [L + 0.6, -1.0], [L + 0.6, 1.0], [-0.6, 1.0]])).with_attr("id", 0.0)
    plate = plate.with_attr("t0", 0.0).with_attr("t1", 0.0).with_attr("fam", 0.0)
    pr = {}
    for n in card.notes:
        lo, hi = pr.get(n["inst"], (999, -1))
        pr[n["inst"]] = (min(lo, n["pitch"]), max(hi, n["pitch"]))
    lane_h = 2.0 / len(LANES)
    P, F, loc, ids, t0, t1, fam = [], [], [], [], [], [], []
    for i, n in enumerate(card.notes):
        li = LANES.index(n["inst"]) if n["inst"] in LANES else LANES.index("pad")
        lo, hi = pr[n["inst"]]
        fr = (n["pitch"] - lo) / max(hi - lo, 1)
        yc = 1.0 - (li + 0.5) * lane_h + (fr - 0.5) * lane_h * 0.62
        x0 = CARD_P * float(Fr(n["q"]))
        x1 = x0 + max(CARD_P * float(Fr(n["ql"])) * 0.94, 0.02)
        hh = 0.0165
        base = len(P)
        for x, y in ((x0, yc - hh), (x1, yc - hh), (x1, yc + hh), (x0, yc + hh)):
            P.append((x, y, 0.02)); loc.append((x, y)); ids.append(i); t0.append(n["t"]); t1.append(n["t"] + n["dur"]); fam.append(FAMILY.get(n["inst"], 1))
        F += [[base, base + 1, base + 2], [base, base + 2, base + 3]]
    holes = Mesh(P, [(0, 0, 1)] * len(P), F).with_attr("kind", 1.0).with_attr("loc", np.array(loc)).with_attr("id", np.array(ids, float).reshape(-1, 1)).with_attr("t0", np.array(t0).reshape(-1, 1))
    holes = holes.with_attr("t1", np.array(t1).reshape(-1, 1)).with_attr("fam", np.array(fam, float).reshape(-1, 1))
    return merge([plate, holes])


def cells_texture():
    cb = PIC.cells()
    rows, w = PIC.pack3(cb)
    tex = [W.texel(int(r), int(g), int(b)) for line in rows for r, g, b in line]
    return N("PixelTexture", W.tex_props(), DEF="Tex_cells", image="%d %d 4 %s" % (w, ROWS, " ".join(tex)), repeatS=False, repeatT=False), w * ROWS * 4


# ---- the camera ---------------------------------------------------------------------------------------
def shot_for(kind, t0, t1, i, cy):
    """The shot vocabulary as data. cy(t) is the height of the weave line; tracking shots follow it (linear, no easing, so the framing stays on the line)."""
    sgn = 1 if i % 2 == 0 else -1
    tm = lambda s: t0 + s * (t1 - t0)
    if kind == "establishing":
        return Shot(kind, t0, t1, lambda s: lerp3((0.0, 3.4, 29.0), (0.0, 4.4, 20.0), s), (0.0, 9.5, -23.8), fov=0.9)
    if kind == "front":
        return Shot(kind, t0, t1, lambda s: lerp3((0.0, 6.4, -6.0), (0.0, 7.0, -9.5), s), (0.0, 6.9, -23.8), fov=0.95)
    if kind == "track":
        return Shot(kind, t0, t1, lambda s: (2.6 * sgn, cy(tm(s)) + 1.0, -15.0), lambda s: (0.4 * sgn, cy(tm(s)) - 0.6, -23.6), fov=0.9, ease=False)
    if kind == "shuttle":
        return Shot(kind, t0, t1, lambda s: (-2.4, cy(tm(s)) + 1.0, -20.0), lambda s: (-1.4, cy(tm(s)) + 0.3, -22.7), fov=0.75, ease=False)
    if kind == "cards":
        return Shot(kind, t0, t1, lambda s: lerp3((-4.6, 12.0, -13.0), (-2.2, 13.2, -14.5), s), (0.4, HEAD_Y - 0.2, -22.0), fov=0.8)
    if kind == "rose":
        return Shot(kind, t0, t1, lambda s: lerp3((0.0, 8.0, -8.0), (0.0, 11.0, -12.0), s), (0.0, 19.0, -24.0), fov=0.95)
    if kind == "nave_high":
        return Shot(kind, t0, t1, lambda s: lerp3((-5.2, 9.5, 5.0), (-3.2, 9.0, -1.0), s), (0.0, 9.0, -23.8), fov=1.0)
    if kind == "side":
        return Shot(kind, t0, t1, lambda s: lerp3((-4.4, 5.0, -3.0), (-3.8, 6.2, -8.0), s), (0.6, 7.5, -23.0), fov=0.95)
    if kind == "floor":
        return Shot(kind, t0, t1, lambda s: lerp3((0.0, 0.9, 6.0), (0.0, 0.9, -4.0), s), (0.0, 4.5, -23.8), fov=0.95)
    if kind == "reveal":
        return Shot(kind, t0, t1, lambda s: lerp3((0.0, 6.5, -8.0), (0.0, 4.6, 27.0), s), (0.0, 7.5, -23.8), fov=0.95)
    raise KeyError(kind)


CYCLE = ["establishing", "front", "track", "cards", "shuttle", "nave_high", "track", "rose", "side", "front", "track", "reveal"]


def shot_list(card):
    blocks = W.shot_blocks(card, phrase_bars=4, dense=6.0)
    ct, cyv = carriage_keys(card)
    cy = lambda t: float(np.interp(t, ct, cyv))
    return [shot_for(CYCLE[i % len(CYCLE)] if i < len(blocks) - 1 else "reveal", b["t0"], b["t1"], i, cy) for i, b in enumerate(blocks)]


# ---- the world ----------------------------------------------------------------------------------------
def build(out=None):
    card = Card("ode")
    w = World(card)
    D = card.D
    comp = [i for i, n in enumerate(card.notes) if n["layer"] == "composer"]

    t_weave = w.table(EventTable("weave", weave_rows(card), D))
    t_chords = w.table(EventTable("chords", chord_rows(card), D))
    cells_node, cell_texels = cells_texture()
    w.stats["texture_bytes"] += cell_texels

    # camera first, so the Viewpoint binds
    shots = shot_list(card)
    vp, ints, rts = W.camera_nodes(shots, D, fov=1.0)
    w.head.append(vp)
    w.add(*ints)
    w.routes += rts
    w.stats["interpolator_keys"] += sum(len(i.attrs["key"].split()) for i in ints)

    # buses that carry the score's features
    for name, (ks, vs) in (("ActBus", activity_keys(card)), ("TensionBus", tension_keys(card)), ("LayerBus", layer_keys(card))):
        w.add(W.interpolator("ScalarInterpolator", name, ks, vs, D, 3))
        w.routes.append(route("FractionBus", "value_changed", name, "set_fraction"))
        w.stats["interpolator_keys"] += len(ks)

    a_, b_ = sweep_vectors(card)
    std = [("u_act", "SFFloat", "inputOutput", 0.0), ("u_tens", "SFFloat", "inputOutput", 0.0)]
    sh_tap = w.sh.make("ShTapestry", "tapestry_vs", "tapestry_fs", [("u_cells", "SFNode", "inputOutput", cells_node), t_weave.field(), ("u_sweepA", "SFVec4f", "inputOutput", vec(*a_)),
                                                                   ("u_sweepB", "SFVec4f", "inputOutput", vec(*b_))] + std)
    sh_nave = w.sh.make("ShNave", "nave_vs", "nave_fs", [("u_layer", "SFFloat", "inputOutput", 0.0)] + std)
    sh_cards = w.sh.make("ShCards", "cards_vs", "cards_fs", list(std))
    sh_rose = w.sh.make("ShRose", "rose_vs", "rose_fs", [t_chords.field()] + std)
    sh_shaft = w.sh.make("ShShaft", "shaft_vs", "shaft_fs", list(std))
    for sh in ("ShTapestry", "ShNave", "ShCards", "ShRose", "ShShaft"):
        w.routes += [route("ActBus", "value_changed", sh, "u_act"), route("TensionBus", "value_changed", sh, "u_tens")]
    w.routes.append(route("LayerBus", "value_changed", "ShNave", "u_layer"))
    use_nave = lambda: N("ComposedShader", USE="ShNave")

    # the static set, the tapestry, the rose window, the light
    w.add(w.shape(nave_meshes(), sh_nave, solid=False, normals=True, color=True))
    w.add(w.shape(tapestry_mesh(), sh_tap, solid=False, normals=False, color=False))
    w.add(w.shape(rose_mesh(), sh_rose, solid=False, normals=False, color=False))
    w.add(w.shape(shafts_mesh(), sh_shaft, blend=True, solid=False, normals=False, color=False))

    # the card chain
    bt, bp = belt_keys(card)
    w.add(N("Transform", w.shape(belt_mesh(card), sh_cards, solid=False, normals=False, color=False), DEF="Belt", translation=vec(0, HEAD_Y, BELT_Z)))
    w.drive("FractionBus", "BeltPos", ("Belt", "translation"), bt, bp, "PositionInterpolator", places=4)

    # the carriage: beam, batten, harness, shuttle; and the cords that tie it to the head
    ct, cyv = carriage_keys(card)
    beam, batten, rods, body, bobbin = carriage_meshes()
    ev = {}
    for n in card.notes:
        ev.setdefault(n["inst"], []).append(n["t"])
    kick_snare = sorted(set(ev.get("kick", []) + ev.get("snare", [])))
    hats = sorted(set(ev.get("hat", [])))
    car_kids = [w.shape(beam, use_nave(), solid=False),
                N("Transform", w.shape(batten, use_nave(), solid=False), DEF="Batten", translation=vec(0, 0.05, -22.7)),
                N("Transform", w.shape(rods, use_nave(), solid=False), DEF="Harness", translation=vec(0, 1.55, -22.6)),
                N("Transform", w.shape(body, use_nave(), solid=False), w.shape(bobbin, use_nave(), solid=False), DEF="Shuttle", translation=vec(-SHUTTLE_X, 0.34, -22.42))]
    w.add(N("Transform", *car_kids, DEF="Carriage", translation=vec(0, TAP_TOP, 0)))
    w.drive("FractionBus", "CarriagePos", ("Carriage", "translation"), ct, [(0.0, y, 0.0) for y in cyv], "PositionInterpolator", places=4)
    bk, bv = hit_keys(kick_snare, 0.0, -0.32, D, lead=0.07, tail=0.16)
    w.drive("FractionBus", "BattenPos", ("Batten", "translation"), bk, [(0.0, 0.05, -22.7 + v) for v in bv], "PositionInterpolator", places=3)
    hk, hv = hit_keys(hats, 0.0, HIT_Y, D, lead=0.03, tail=0.07)
    w.drive("FractionBus", "HarnessPos", ("Harness", "translation"), hk, [(0.0, 1.55 + v, -22.6) for v in hv], "PositionInterpolator", places=3)
    sk, sx = shuttle_keys(card)
    w.drive("FractionBus", "ShuttlePos", ("Shuttle", "translation"), sk, [(x, 0.34, -22.42) for x in sx], "PositionInterpolator", places=3)
    w.add(N("Transform", w.shape(cords_mesh(), use_nave(), solid=False), DEF="Cords", translation=vec(0, TAP_TOP + 0.9, 0), scale=vec(1, 0.4, 1)))
    head_bottom = HEAD_Y - 1.2 - 0.11
    w.drive("FractionBus", "CordsPos", ("Cords", "translation"), ct, [(0.0, y + 0.9, 0.0) for y in cyv], "PositionInterpolator", places=3)
    w.drive("FractionBus", "CordsScale", ("Cords", "scale"), ct, [(1.0, max(head_bottom - (y + 0.9), 0.05), 1.0) for y in cyv], "PositionInterpolator", places=3)

    # what each row of each table means, for the page's hover and the Score witness
    drawn = dict(weave=[[e[5] for e in r] for r in t_weave.rows], chords=[[e[5] for e in r] for r in t_chords.rows], holes=list(range(len(card.notes))),
                 layers=[dict(name=L["name"], section=L["sec"], insts=list(L["insts"])) for L in LAYERS],
                 hash=[[x, y, owner_hash(x, y)] for x, y in ((0, 0), (1, 0), (0, 1), (17, 5), (255, 383), (128, 192), (100, 300), (3, 77))])
    extra = dict(notes=len(card.notes), composer_notes=len(comp), cards=int(card.total_q), cells=ROWS * COLS, layers=[L["name"] for L in LAYERS], shots=len(shots))
    rep = W.write_world(w, "Ode to Joy: the Jacquard tapestry", "Every note is a hole in the card chain, and each statement of the theme weaves one colour of the picture.", extra, background=(0.0, 0.0, 0.01), out=out)
    import json
    with open(os.path.join(out or W.OUT, "ode.map.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(drawn, separators=(",", ":")) + "\n")
    return rep


if __name__ == "__main__":
    r = build()
    print({k: v for k, v in r.items() if k not in ("tables", "layers")})
    print("tables", r["tables"])
