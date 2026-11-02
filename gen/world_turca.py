#!/usr/bin/env python3
"""World 2, Rondo alla Turca: the pinned barrel and the Janissary automata. Writes build/worlds/turca.x3d (+ report and the element map).

Score-true by construction (spec: the pin rule). Every composer note in the card is a pin on the barrel (1,613 written heads, repeats reuse their pin), a tooth of the comb (one per
pitch, MIDI 38 to 88) and a tile of the floor mandala (12 sectors on the circle of fifths by pitch class, 5 rings by octave). Each of the three is a row of an event texture
filled from the card, so a shader decides what glows from u_time and nothing else. The barrel has one band per section and turns once per section pass, so a pin's angle is its onset
inside the pass; the barrel slides to the next band at every section change. Arrangement notes drive the automata (strike = lift 120 ms before, land on the event, settle 200 ms after).

Layout, metres, Y up, the viewer looks toward -Z: the mandala is centred on the origin (radius 1.4 to 6.4), the barrel machine stands at z = -9 behind it, a ring of 24 arcade bays
at radius 13.5 carries the dome, the automata stand in an arc to the left.
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

# ---- layout ---------------------------------------------------------------------------------------
LANE = 0.02                                   # metres between neighbouring pins and between comb teeth
PITCH0, PITCH1 = 38, 88                       # the comb: one tooth per MIDI pitch, 51 teeth
NT = PITCH1 - PITCH0 + 1
BAND_W = NT * LANE
BARREL_R, BARREL_Y, BARREL_Z = 1.7, 2.5, -9.0
PIN_H, PIN_W = 0.034, LANE * 0.7
FLOOR_R0, FLOOR_R1 = 1.4, 6.4
DOME_R, DOME_Y = 14.4, 6.2
ARC_R, N_BAYS = 13.5, 24
SHIFT_S = 0.32                                # the barrel slides to its next band in at most this long, landing on the first note of the new pass
QPM = 126.0


STONE, PLASTER, BRASS, STEEL = lin(190, 160, 120), lin(214, 176, 128), lin(232, 188, 108), lin(176, 184, 196)
BRONZE, ALCOVE, WOOD = lin(150, 92, 38), lin(70, 82, 130), lin(150, 100, 60)
PORCELAIN, COBALT, TURQUOISE, TOMATO = lin(236, 232, 220), lin(20, 60, 150), lin(24, 156, 156), lin(190, 52, 36)
LAMP = ("u_lampI", "SFFloat", "inputOutput", 1.0)


def sector_of(pc):
    return (pc * 7) % 12                       # the circle of fifths: C G D A E B F# C# G# D# A# F


def ring_of(pitch):
    return int(min(max((pitch - 36) // 12, 0), 4))


def pol(r, a, y=0.0):
    """A point at radius r and angle a clockwise from -Z (the far side), so sector 0 is straight ahead of a viewer on +Z."""
    return (r * math.sin(a), y, -r * math.cos(a))


# ---- the pins ---------------------------------------------------------------------------------------
def band_names(card):
    out = []
    for p in card.passes:
        if p["id"] not in out:
            out.append(p["id"])
    return out


def band_x(k, n):
    return (k - (n - 1) / 2) * BAND_W


def pass_by(card):
    return {(p["id"], p["rep"]): p for p in card.passes}


def pass_at(card, t):
    """The form pass that is turning the barrel at performed time t (half open: t0 <= t < t1). A grace note sounds just before its beat, so one that opens a section is in the
    pass before it: the barrel has not clicked to the new band yet, and the pin goes where the barrel really is."""
    last = None
    for p in card.passes:
        if p["t0"] <= t + 1e-9:
            last = p
        else:
            break
    return last


ANGLE_TOL = 2e-4            # rad: the card keeps times to a microsecond, so a note's two statements agree on the angle to about 1e-6; two pins closer than this are one pin


def _cluster(members):
    """members = [(note index, pass, theta)]; group those whose angles agree within ANGLE_TOL (circularly)."""
    members = sorted(members, key=lambda m: m[2])
    out = []
    for m in members:
        if out and m[2] - out[-1][0][2] <= ANGLE_TOL:
            out[-1].append(m)
        else:
            out.append([m])
    if len(out) > 1 and out[0][0][2] + TAU - out[-1][-1][2] <= ANGLE_TOL:
        out[0] = out.pop() + out[0]
    return out


def make_pins(card):
    """One pin per written note head (card src); reps of a section reuse their pin. A pin sits on the band and at the angle the barrel has when its note sounds (pass_at), so a
    note meets the comb whatever its label says. Notes of one src that land on another band or angle get a pin of their own. Returns dicts sorted by band, angle, pitch."""
    names = band_names(card)
    groups = {}
    for i, n in enumerate(card.notes):
        if n["layer"] == "composer":
            p = pass_at(card, n["t"])
            theta = (TAU * (n["t"] - p["t0"]) / (p["t1"] - p["t0"])) % TAU
            groups.setdefault((n["src"], names.index(p["id"])), []).append((i, p, theta))
    pins = []
    for (src, band), members in groups.items():
        for cl in _cluster(members):
            idxs = [m[0] for m in cl]
            p, theta = cl[0][1], cl[0][2]
            dur = max(card.notes[i]["dur"] for i in idxs)
            dpsi = TAU * dur / max(p["t1"] - p["t0"], 1e-6)
            pins.append(dict(src=src, band=band, section=p["id"], theta=theta, dpsi=dpsi, pitch=card.notes[idxs[0]]["pitch"], notes=idxs))
    pins.sort(key=lambda d: (d["band"], d["theta"], d["pitch"], d["src"]))
    for k, d in enumerate(pins):
        d["i"] = k
    return pins


def bent_bar(xc, w, r0, h, psi0, dpsi, nseg):
    """A bar standing on the barrel: centre x, width w, from radius r0 up to r0 + h, spanning angle psi0 .. psi0 + dpsi (from +Z toward +Y, about X). Rings of four shared corners;
    the shader takes flat normals from screen derivatives, so the file carries no Normal or Color array for the 1,613 pins."""
    P = []
    for j in range(nseg + 1):
        a = psi0 + dpsi * j / nseg
        s_, c_ = math.sin(a), math.cos(a)
        P += [(xc - w / 2, r0 * s_, r0 * c_), (xc + w / 2, r0 * s_, r0 * c_), (xc + w / 2, (r0 + h) * s_, (r0 + h) * c_), (xc - w / 2, (r0 + h) * s_, (r0 + h) * c_)]
    F = []
    for j in range(nseg):
        o, q = 4 * j, 4 * j + 4
        F += [[o + 3, o + 2, q + 2], [o + 3, q + 2, q + 3], [o + 0, o + 3, q + 3], [o + 0, q + 3, q + 0], [o + 2, o + 1, q + 1], [o + 2, q + 1, q + 2]]
    last = 4 * nseg
    F += [[0, 1, 2], [0, 2, 3], [last, last + 2, last + 1], [last, last + 3, last + 2]]
    return Mesh(P, np.zeros((len(P), 3)), F)


def pins_mesh(pins, nbands):
    parts, halos = [], []
    for d in pins:
        xc = band_x(d["band"], nbands) + (d["pitch"] - (PITCH0 + PITCH1) // 2) * LANE
        dpsi = max(d["dpsi"], 0.014 / BARREL_R)
        nseg = max(1, int(math.ceil(dpsi / math.radians(9))))
        parts.append(bent_bar(xc, PIN_W, BARREL_R - 0.004, PIN_H, d["theta"], dpsi, nseg).with_attr("pin", float(d["i"])))
        a = d["theta"] + dpsi / 2
        r = BARREL_R + PIN_H * 0.6
        c = (xc, r * math.sin(a), r * math.cos(a))
        for cx, cy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            halos.append((c, (cx, cy), d["i"]))
    P = np.array([h[0] for h in halos])
    n = len(pins)
    hm = Mesh(P, np.zeros((len(P), 3)), [[4 * k, 4 * k + 1, 4 * k + 2] for k in range(n)] + [[4 * k, 4 * k + 2, 4 * k + 3] for k in range(n)],
              None, {"corner": [h[1] for h in halos], "pin": [float(h[2]) for h in halos]})
    return merge(parts), hm


def barrel_mesh(nbands):
    half = nbands * BAND_W / 2 + 0.4
    prof = [(0.0, -half - 0.62), (0.26, -half - 0.62), (0.26, -half - 0.14), (BARREL_R + 0.2, -half - 0.14), (BARREL_R + 0.2, -half - 0.02), (BARREL_R + 0.03, -half - 0.02), (BARREL_R, -half + 0.05)]
    for k in range(nbands + 1):
        y = (k - nbands / 2) * BAND_W
        prof += [(BARREL_R, y - 0.025), (BARREL_R + 0.014, y - 0.012), (BARREL_R + 0.014, y + 0.012), (BARREL_R, y + 0.025)]
    prof += [(BARREL_R, half - 0.05), (BARREL_R + 0.03, half + 0.02), (BARREL_R + 0.2, half + 0.02), (BARREL_R + 0.2, half + 0.14), (0.26, half + 0.14), (0.26, half + 0.62), (0.0, half + 0.62)]
    return M.lathe(prof, seg=96).transformed(R(Z_AXIS, -math.pi / 2))


# ---- the comb ---------------------------------------------------------------------------------------
def tooth_len(p):
    return 0.42 + (PITCH1 - p) / (PITCH1 - PITCH0) * 0.80          # lower notes have longer teeth, as on a real comb


def blade(x0, x1, y0, y1, z_tip, z_base, nseg=5):
    quads = []
    zs = [z_tip + (z_base - z_tip) * j / nseg for j in range(nseg + 1)]
    for j in range(nseg):
        a, b = zs[j], zs[j + 1]
        quads += [[(x0, y1, a), (x0, y1, b), (x1, y1, b), (x1, y1, a)], [(x0, y0, b), (x0, y0, a), (x1, y0, a), (x1, y0, b)],
                  [(x0, y0, a), (x0, y1, a), (x0, y1, b), (x0, y0, b)], [(x1, y0, b), (x1, y1, b), (x1, y1, a), (x1, y0, a)]]
    quads += [[(x0, y0, z_tip), (x1, y0, z_tip), (x1, y1, z_tip), (x0, y1, z_tip)]]
    return M._flat(quads)


def comb_mesh():
    z_tip = BARREL_Z + BARREL_R + PIN_H * 0.45
    parts = []
    for p in range(PITCH0, PITCH1 + 1):
        xc = (p - (PITCH0 + PITCH1) // 2) * LANE
        zb = z_tip + tooth_len(p)
        m = blade(xc - 0.0058, xc + 0.0058, BARREL_Y - 0.0025, BARREL_Y + 0.0025, z_tip, zb)
        along = np.clip((zb - m.P[:, 2]) / (zb - z_tip), 0, 1)
        parts.append(m.with_attr("tooth", float(p - PITCH0)).with_attr("along", along.reshape(-1, 1)))
    return merge(parts)


def comb_mount():
    """A brass bedplate under the teeth, a bar along their roots, and a bench carrying both."""
    z_tip = BARREL_Z + BARREL_R + PIN_H * 0.45
    za, zb = z_tip + tooth_len(PITCH0), z_tip + tooth_len(PITCH1)
    x0, x1 = -NT * LANE / 2 - 0.06, NT * LANE / 2 + 0.06
    y0, y1 = BARREL_Y - 0.075, BARREL_Y - 0.035
    zt0, zt1 = z_tip - 0.04, z_tip - 0.04
    zr0, zr1 = za + 0.06, zb + 0.06
    top = [(x0, y1, zt0), (x0, y1, zr0), (x1, y1, zr1), (x1, y1, zt1)]
    bot = [(x0, y0, zt0), (x1, y0, zt1), (x1, y0, zr1), (x0, y0, zr0)]
    side = lambda a, b: [(a[0], y0, a[2]), (b[0], y0, b[2]), (b[0], y1, b[2]), (a[0], y1, a[2])]
    plate = M._flat([top, bot, side((x0, 0, zt0), (x0, 0, zr0))[::-1], side((x1, 0, zr1), (x1, 0, zt1))[::-1], side((x1, 0, zt1), (x0, 0, zt0))[::-1], side((x0, 0, zr0), (x1, 0, zr1))[::-1]])
    L = math.hypot(x1 - x0, zr1 - zr0)
    ang = math.atan2(zr0 - zr1, x1 - x0)
    bar = M.box(L, 0.1, 0.1).transformed(compose(T(0, BARREL_Y - 0.01, (zr0 + zr1) / 2), R(Y_AXIS, ang)))
    zc, top = (za + zb) / 2 + 0.1, BARREL_Y - 0.1
    col = [M.cylinder(0.42, 0.42, 0.14, 28).transformed(T(0, 0.5, zc)), M.cylinder(0.3, 0.2, top - 0.5 - 0.14 - 0.1, 28).transformed(T(0, 0.64, zc)),
           M.torus(0.25, 0.045, 28, 8).transformed(T(0, 1.15, zc)), M.torus(0.25, 0.045, 28, 8).transformed(T(0, 1.95, zc)),
           M.cylinder(0.26, 0.26, 0.1, 28).transformed(T(0, top - 0.1, zc)), M.cylinder(0.12, 0.12, 0.1, 20).transformed(T(0, top - 0.02, zc))]
    arm = M.box(0.1, 0.1, abs(zc - zr0)).transformed(T(0, top, (zc + zr0) / 2))
    return merge([plate, bar, arm] + col)


# ---- the floor, the hall -----------------------------------------------------------------------------
def tiles_mesh():
    P, Nn, F, A = [], [], [], {"tile": [], "uv": []}
    seg = 4
    for ring in range(5):
        r0 = FLOOR_R0 + (FLOOR_R1 - FLOOR_R0) * ring / 5
        r1 = FLOOR_R0 + (FLOOR_R1 - FLOOR_R0) * (ring + 1) / 5
        for sec in range(12):
            a0, a1 = (sec - 0.5) * TAU / 12, (sec + 0.5) * TAU / 12
            base = len(P)
            for i in range(seg + 1):
                u = i / seg
                a = a0 + (a1 - a0) * u
                for v, r in ((0.0, r0), (1.0, r1)):
                    P.append(pol(r, a, 0.0))
                    Nn.append((0.0, 1.0, 0.0))
                    A["tile"].append(float(ring * 12 + sec))
                    A["uv"].append((u, v))
            for i in range(seg):
                a, b, c, d = base + 2 * i, base + 2 * i + 1, base + 2 * i + 2, base + 2 * i + 3
                F += [[a, b, c], [b, d, c]]
    return Mesh(P, Nn, F, np.ones((len(P), 3)), A)


def lantern_positions():
    return [pol(12.55, (k + 0.5) * TAU / N_BAYS, 4.1) for k in range(N_BAYS)]


def hall_part(mesh, mat, albedo=(1.0, 1.0, 1.0)):
    return mesh.colored(albedo).with_attr("mat", float(mat))


def outer_floor():
    """A polar grid of shared vertices from the mandala's edge to the wall; the flagstones are drawn by the shader (hall_fs, material 0)."""
    nr, na = 10, 96
    P, Nn, F = [], [], []
    for i in range(nr + 1):
        r = FLOOR_R1 - 0.02 + (14.35 - FLOOR_R1) * i / nr
        for j in range(na + 1):
            P.append(pol(r, j * TAU / na))
            Nn.append((0.0, 1.0, 0.0))
    for i in range(nr):
        for j in range(na):
            a, b = i * (na + 1) + j, i * (na + 1) + j + 1
            c, d = a + na + 1, b + na + 1
            F += [[a, b, c], [b, d, c]]
    return hall_part(Mesh(P, Nn, F), 0)


def hub_mesh():
    return hall_part(M.disc(FLOOR_R0 - 0.02, 64, True).transformed(T(0, 0.002, 0)), 4, BRASS)


def arcade_mesh():
    parts = []
    bay = M.arch_prism(2.75, 4.9, 1.1, seg=16, thickness=0.42)
    for k in range(N_BAYS):
        a = (k + 0.5) * TAU / N_BAYS
        parts.append(bay.transformed(compose(T(*pol(ARC_R, a)), R(Y_AXIS, -a))))
    cornice = M.torus(14.0, 0.28, 96, 8).transformed(T(0, 6.35, 0))
    slab = hall_part(merge(parts + [cornice]), 1, PLASTER)
    wall = hall_part(M.cylinder(14.35, 14.35, 6.4, 96, caps=False), 2, ALCOVE)
    return slab, wall


def plinth_mesh():
    parts = [M.box(15.0, 0.5, 5.0).transformed(T(0, 0.25, BARREL_Z - 0.4))]
    for k in range(3):
        parts.append(M.box(15.0 - 0.8 * k, 0.17, 0.6).transformed(T(0, 0.085, BARREL_Z + 2.5 + 0.3 + 0.6 * k)))
    stone = hall_part(merge(parts), 1, STONE)
    half = 12 * BAND_W / 2 + 0.4
    brass = []
    for s_ in (-1, 1):
        x = s_ * (half + 0.4)
        brass.append(M.box(0.7, 1.7, 1.2).transformed(T(x, 0.5 + 0.85, BARREL_Z)))
        brass.append(M.cylinder(0.5, 0.5, 0.15, 24).transformed(T(x, 0.5 + 1.7, BARREL_Z)))
    return stone, hall_part(merge(brass), 3, BRONZE)


def dome_mesh():
    prof = [(DOME_R * math.sin(math.radians(a)), DOME_R * math.cos(math.radians(a))) for a in np.linspace(90, 0, 25)]
    return M.lathe(prof, seg=96)


# ---- lanterns ---------------------------------------------------------------------------------------
def lantern_meshes():
    frames, sprites = [], []
    for k, c in enumerate(lantern_positions()):
        ph = k * 0.7
        anchor = (c[0] * 0.995, c[1] + 1.3, c[2] * 0.995)
        glass = M.cylinder(0.14, 0.14, 0.38, 10).transformed(T(0, -0.19, 0)).colored((1.0, 0.7, 0.3)).with_attr("glass", 1.0)
        capt = M.cylinder(0.04, 0.19, 0.12, 10).transformed(T(0, 0.19, 0)).colored(BRASS).with_attr("glass", 0.0)
        capb = M.cylinder(0.12, 0.05, 0.1, 10).transformed(T(0, -0.29, 0)).colored(BRASS).with_attr("glass", 0.0)
        chain = M.cylinder(0.012, 0.012, 1.1, 5).transformed(T(0, 0.3, 0)).colored(BRASS).with_attr("glass", 0.0)
        m = merge([glass, capt, capb, chain]).transformed(T(*c))
        m = m.with_attr("anchor", anchor).with_attr("phase", ph)
        frames.append(m)
        for cx, cy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            sprites.append((c, (cx, cy), ph, anchor))
    P = np.array([s[0] for s in sprites])
    n = len(lantern_positions())
    sm = Mesh(P, np.tile((0.0, 0.0, 1.0), (len(P), 1)), [[4 * k, 4 * k + 1, 4 * k + 2] for k in range(n)] + [[4 * k, 4 * k + 2, 4 * k + 3] for k in range(n)],
              np.tile((1.0, 0.62, 0.28), (len(P), 1)),
              {"corner": [s[1] for s in sprites], "size": [1.7] * len(P), "phase": [s[2] for s in sprites], "anchor": [s[3] for s in sprites]})
    return merge(frames), sm


# ---- the band ---------------------------------------------------------------------------------------
AUTOMATA = [("davul", ("davul",), -128), ("cymbal", ("cymbal",), -112), ("tom", ("tom",), -96), ("triangle", ("triangle",), -80), ("jingle", ("jingle",), -64)]
ARM_REST, ARM_UP, ARM_HIT = 0.45, 1.55, 0.05          # radians forward of hanging straight down
AUTO_R = 8.2


def arm_mesh(held=None):
    arm = M.box(0.11, 0.62, 0.11).transformed(T(0, -0.31, 0)).colored(PORCELAIN)
    hand = M.sphere(0.07, 10, 6).transformed(T(0, -0.66, 0)).colored(BRASS)
    parts = [arm, hand]
    if held == "mallet":
        parts += [M.cylinder(0.015, 0.015, 0.4, 6).transformed(compose(T(0, -0.66, 0), R(X_AXIS, -math.pi / 2))).colored(BRASS), M.sphere(0.07, 10, 6).transformed(T(0, -0.66, 0.4)).colored(TOMATO)]
    if held == "rod":
        parts += [M.cylinder(0.01, 0.01, 0.35, 6).transformed(compose(T(0, -0.66, 0), R(X_AXIS, -math.pi / 2))).colored(STEEL)]
    if held == "staff":
        parts += [M.cylinder(0.02, 0.02, 2.4, 8).transformed(T(0, -0.66 - 0.5, 0)).colored(BRASS), M.torus(0.18, 0.025, 20, 6).transformed(compose(T(0, 1.55, 0), R(X_AXIS, math.pi / 2))).colored(BRASS),
                  M.sphere(0.07, 8, 6).transformed(T(0, 1.8, 0)).colored(TOMATO)]
    if held == "plate":
        parts += [M.cylinder(0.3, 0.3, 0.015, 24).transformed(compose(T(0, -0.66, 0.05), R(X_AXIS, math.pi / 2))).colored(BRASS)]
    return merge(parts)


def automaton_static(kind):
    base = M.cylinder(0.45, 0.4, 0.12, 20).colored(TURQUOISE)
    ped = M.cylinder(0.26, 0.22, 0.85, 16).transformed(T(0, 0.12, 0)).colored(BRASS)
    torso = M.lathe([(0.22, 0.97), (0.31, 1.15), (0.29, 1.5), (0.22, 1.78)], 18).colored(COBALT)
    sash = M.cylinder(0.315, 0.315, 0.1, 18, caps=False).transformed(T(0, 1.22, 0)).colored(TOMATO)
    head = M.sphere(0.19, 16, 10).transformed(T(0, 1.98, 0)).colored(PORCELAIN)
    hat = M.cylinder(0.2, 0.13, 0.36, 14).transformed(T(0, 2.12, 0)).colored(PORCELAIN)
    band = M.cylinder(0.205, 0.205, 0.06, 14, caps=False).transformed(T(0, 2.14, 0)).colored(TOMATO)
    mark = M.box(0.07, 0.07, 0.01).transformed(compose(T(0, 1.99, 0.185), R(Z_AXIS, math.pi / 4))).colored(COBALT)
    parts = [base, ped, torso, sash, head, hat, band, mark]
    if kind == "davul":
        drum = M.cylinder(0.42, 0.42, 0.34, 28).transformed(compose(T(0, 1.15, 0.0), R(X_AXIS, math.pi / 2)))
        parts += [drum.transformed(T(0, 0, 0.55)).colored(TOMATO), M.cylinder(0.36, 0.36, 0.01, 28).transformed(compose(T(0, 1.15, 0.86), R(X_AXIS, math.pi / 2))).colored(PORCELAIN)]
    if kind == "tom":
        for s in (-1, 1):
            parts += [M.sphere(0.24, 16, 8).transformed(compose(T(s * 0.32, 1.02, 0.42), S(1, 0.7, 1))).colored(BRASS), M.disc(0.235, 18, True).transformed(T(s * 0.32, 1.19, 0.42)).colored(PORCELAIN)]
    if kind == "triangle":
        parts += [M.torus(0.17, 0.012, 3, 6).transformed(compose(T(-0.34, 1.05, 0.4), R(X_AXIS, math.pi / 2))).colored(STEEL)]
    if kind == "jingle":
        parts += [M.cylinder(0.025, 0.025, 1.9, 8).transformed(T(0.34, 0.1, 0.1)).colored(BRASS)]
    return merge(parts)


def automata_nodes(w, card):
    """Five automata. Each strike arm is a Transform driven by an OrientationInterpolator whose keys come from the card events of its instruments."""
    nodes = []
    ev_by_inst = {}
    for n in card.notes:
        ev_by_inst.setdefault(n["inst"], []).append(n["t"])
    for k, (kind, insts, deg) in enumerate(AUTOMATA):
        a = math.radians(deg)
        pos = pol(AUTO_R, a)
        face = math.atan2(-pos[0], -pos[2])                    # turn +Z toward the centre of the courtyard
        held = {"davul": "mallet", "cymbal": "plate", "tom": "rod", "triangle": "rod", "jingle": "staff"}[kind]
        name = "Band_" + kind
        children = [w.shape(automaton_static(kind), auto_shader(w), solid=False)]
        times = sorted(t for inst in insts for t in ev_by_inst.get(inst, []))
        by_arm = arm_events(kind, times)
        for s_ in (-1, 1):
            hold = held if s_ == 1 else ("plate" if kind == "cymbal" else None)
            adef = "%s_arm%s" % (name, "R" if s_ == 1 else "L")
            children.append(N("Transform", w.shape(arm_mesh(hold), auto_shader(w), solid=False), DEF=adef, translation=vec(s_ * 0.36, 1.66, 0.0), rotation=vec(1, 0, 0, ARM_REST)))
            if by_arm[s_]:                                     # an arm with no event of its own stays at rest and is driven by nothing
                keys, vals = strike_keys(by_arm[s_], w.D)
                w.drive("FractionBus", adef + "_rot", (adef, "rotation"), keys, [(1.0, 0.0, 0.0, v) for v in vals], "OrientationInterpolator")
        nodes.append(N("Transform", *children, translation=vec(*pos), rotation=vec(0, 1, 0, face), DEF=name))
    return nodes


def arm_events(kind, times):
    """Which arm strikes which event: the drum and the toms alternate hands, the cymbals clash (both arms on every event), the triangle and the jingle staff are the right hand's. Every event moves an arm."""
    if kind in ("davul", "tom"):
        return {1: times[0::2], -1: times[1::2]}
    if kind == "cymbal":
        return {1: list(times), -1: list(times)}
    return {1: list(times), -1: []}


def strike_keys(times, D):
    """Keys (seconds) and arm angles for a list of event times: lift 120 ms before, land on the event, settle 200 ms after. Keys that would cross a neighbour's are dropped."""
    out = [(0.0, ARM_REST)]
    for i, t in enumerate(times):
        nxt = times[i + 1] if i + 1 < len(times) else D
        for tt, v in ((t - 0.12, ARM_UP), (t, ARM_HIT), (min(t + 0.2, (t + nxt - 0.12) / 2 if nxt - t < 0.32 else t + 0.2), ARM_REST)):
            if tt > out[-1][0] + 1e-4 and tt < D:
                out.append((tt, v))
    out.append((D, ARM_REST))
    return [t for t, _ in out], [v for _, v in out]


# ---- shaders and buses --------------------------------------------------------------------------------
def metal_shader(w, name, gloss, tint, brushed=0.0, ring=0.8, vs="metal_vs", fs="metal_fs", extra=(), albedo=(1.0, 1.0, 1.0), vcol=0.0, flat=0.0):
    """A lantern-lit surface (metal_lib). vcol 1 reads albedo from the vertex Color; otherwise `albedo` is used and the file needs no Color array."""
    fields = [("u_envTop", "SFVec3f", "inputOutput", vec(0.02, 0.04, 0.11)), ("u_envHor", "SFVec3f", "inputOutput", vec(0.20, 0.11, 0.06)), ("u_envLow", "SFVec3f", "inputOutput", vec(0.05, 0.035, 0.03)),
              ("u_tint", "SFVec3f", "inputOutput", vec(*tint)), ("u_albedo", "SFVec3f", "inputOutput", vec(*albedo)), ("u_ring", "SFFloat", "inputOutput", ring), ("u_gloss", "SFFloat", "inputOutput", gloss),
              ("u_brushed", "SFFloat", "inputOutput", brushed), ("u_vcol", "SFFloat", "inputOutput", vcol), ("u_flat", "SFFloat", "inputOutput", flat), LAMP]
    return w.sh.make(name, vs, fs, fields + list(extra))


def auto_shader(w):
    return w.shared("ShAuto", lambda: metal_shader(w, "ShAuto", 0.4, (1.0, 0.92, 0.8), 0.0, 0.5, vcol=1.0))


def key_index(k):
    return {"a": 0, "C": 0, "A": 1, "f#": 2}.get(k, 0)


def state_buses(w, card):
    """SectionBus (band index at each pass start), KeyBus (palette 0 minor, 1 major, 2 F# minor, crossfaded over 0.8 s before each change) and OpenBus (the dome opens on the final hit)."""
    names = band_names(card)
    tt, sv = [0.0], [float(names.index(card.passes[0]["id"]))]
    for p in card.passes[1:]:
        v = float(names.index(p["id"]))
        if v != sv[-1]:
            tt += [p["t0"] - W.CUT_EPS, p["t0"]]
            sv += [sv[-1], v]
    tt.append(w.D); sv.append(sv[-1])
    w.add(W.interpolator("ScalarInterpolator", "SectionBus", tt, sv, w.D, 1))
    kt, kv = [0.0], [float(key_index(card.key_map[0]["key"]))]
    for e in card.key_map[1:]:
        v = float(key_index(e["key"]))
        if v != kv[-1]:
            kt += [max(e["t"] - 0.8, kt[-1] + 0.01), e["t"]]
            kv += [kv[-1], v]
    kt.append(w.D); kv.append(kv[-1])
    w.add(W.interpolator("ScalarInterpolator", "KeyBus", kt, kv, w.D, 1))
    last = max(n["t"] for n in card.composer())
    w.add(W.interpolator("ScalarInterpolator", "OpenBus", [0.0, last - 0.2, last + 2.6, w.D], [0.0, 0.0, 1.0, 1.0], w.D, 3))
    w.routes += [route("FractionBus", "value_changed", b, "set_fraction") for b in ("SectionBus", "KeyBus", "OpenBus")]
    w.stats["interpolator_keys"] += len(tt) + len(kt) + 4
    return names


def shift_windows(card, names):
    """(depart, arrive, to_band) for every change of band. The barrel clicks to the next band in the gap before the new pass's first main (not grace) onset, over as much of that gap
    as there is up to SHIFT_S. Grace notes that open a section sound before that onset, so they ride the old band; the gap is then the 60 ms between the last grace and the beat."""
    comp = card.composer()
    onsets = sorted(n["t"] for n in comp)
    main = {}
    for n in comp:
        if not n.get("g"):
            main.setdefault((n["section"], n["rep"]), []).append(n["t"])
    out, last_arrive = [], 0.0
    for prev, p in zip(card.passes, card.passes[1:]):
        if prev["id"] == p["id"]:
            continue
        arrive = min(main[(p["id"], p["rep"])])
        before = [t for t in onsets if t < arrive - 1e-9]
        depart = max(before[-1] if before else 0.0, arrive - SHIFT_S, last_arrive + 1e-3)
        out.append((depart, arrive, names.index(p["id"])))
        last_arrive = arrive
    return out


def barrel_keys(card, names, D):
    """(rotation times, cumulative angles, position times, positions): the barrel turns once per section pass in 45 degree keys, and slides to the next band in a shift window.
    Angles accumulate, so the keys are continuous; the interpolator only ever sees steps smaller than half a turn. The last pass stops when its last note has died away (a pin at
    the start of that band would otherwise come to rest on the comb)."""
    t_stop = max(n["t"] + n["dur"] for n in card.composer()) + 0.1
    rt, rv = [0.0], [0.0]
    turns = 0.0
    for j, p in enumerate(card.passes):
        t1 = min(p["t1"], t_stop) if j == len(card.passes) - 1 else p["t1"]
        for k in range(0, 9):
            t = p["t0"] + (t1 - p["t0"]) * k / 8
            if t > rt[-1] + 1e-4:
                rt.append(t); rv.append(turns + TAU * (t - p["t0"]) / (p["t1"] - p["t0"]))
        turns += TAU
    rt.append(D); rv.append(rv[-1])
    n = len(names)
    pt, pv = [0.0], [(-band_x(names.index(card.passes[0]["id"]), n), BARREL_Y, BARREL_Z)]
    for depart, arrive, b in shift_windows(card, names):
        pt += [depart, arrive]
        pv += [pv[-1], (-band_x(b, n), BARREL_Y, BARREL_Z)]
    pt.append(D); pv.append(pv[-1])
    return rt, rv, pt, pv


def barrel_motion(w, card, names):
    rt, rv, pt, pv = barrel_keys(card, names, w.D)
    w.drive("FractionBus", "BarrelRot", ("Barrel", "rotation"), rt, [(1.0, 0.0, 0.0, a) for a in rv], "OrientationInterpolator", places=4)
    w.drive("FractionBus", "BarrelPos", ("Barrel", "translation"), pt, pv, "PositionInterpolator", places=4)


# ---- the camera ---------------------------------------------------------------------------------------
COMB = (0.0, BARREL_Y - 0.05, BARREL_Z + BARREL_R + 0.1)




def shot_for(kind, t0, t1, i):
    """The shot vocabulary (spec: establishing, machine, pin, detail, reveal) as data. Eyes and targets in metres."""
    sgn = 1 if i % 2 == 0 else -1
    if kind == "establishing":
        return Shot(kind, t0, t1, lambda s: lerp3((0.0, 3.0, 12.2), (0.0, 2.8, 9.6), s), (0.0, 2.7, -6.0), fov=0.9)
    if kind == "machine":
        return Shot(kind, t0, t1, lambda s: lerp3((sgn * 4.6, 3.4, -1.6), (sgn * 3.6, 3.0, -2.6), s), (0.0, 2.5, -8.2), fov=0.95)
    if kind == "pins":
        return Shot(kind, t0, t1, lambda s: lerp3((sgn * 0.9, 3.15, -5.3), (sgn * 0.6, 2.95, -5.7), s), (0.0, 2.5, -7.9), fov=0.8)
    if kind == "teeth":
        return Shot(kind, t0, t1, lambda s: lerp3((0.5 * sgn, 3.45, -6.0), (0.25 * sgn, 3.0, -6.55), s), (0.0, 2.5, -7.2), fov=0.95)
    if kind == "floor_high":
        return Shot(kind, t0, t1, orbit((0, 0, 0), 5.0, 10.2, 0.2 * sgn, 0.55 * sgn), (0.0, 0.0, -0.8), fov=1.0, up=(0.0, 0.0, -1.0) if False else (0.0, 1.0, 0.0))
    if kind == "floor_low":
        return Shot(kind, t0, t1, lambda s: lerp3((3.8 * sgn, 0.9, 3.4), (2.2 * sgn, 0.8, 2.2), s), (-1.0 * sgn, 0.15, -3.0), fov=1.0)
    if kind == "dome_up":
        return Shot(kind, t0, t1, (0.0, 1.5, 0.0), lambda s: lerp3((0.0, 10.0, 0.25), (0.0, 10.0, 0.9), s), fov=1.45, up=(0.0, 0.0, -1.0))
    if kind == "automata":
        c = pol(AUTO_R, math.radians(-96), 1.5)
        return Shot(kind, t0, t1, lambda s: lerp3((-3.0, 2.0, 5.2), (-1.2, 2.0, 4.0), s), c, fov=1.0)
    if kind == "reveal":
        return Shot(kind, t0, t1, lambda s: lerp3((0.0, 2.8, -4.6), (0.0, 5.5, 13.5), s), lambda s: lerp3((0.0, 2.6, -8.6), (0.0, 3.2, -4.0), s), fov=1.0)
    raise KeyError(kind)


def shot_list(card):
    blocks = W.shot_blocks(card, phrase_bars=4, dense=6.0)
    cycle = ["pins", "machine", "floor_high", "teeth", "automata", "floor_low", "machine", "dome_up"]
    shots, prev, c = [], None, 0
    for i, b in enumerate(blocks):
        if i == 0:
            kind = "establishing"
        elif i == len(blocks) - 1:
            kind = "reveal"
        else:
            kind = cycle[c % len(cycle)]
            c += 1
            if kind == prev:
                kind = cycle[c % len(cycle)]
                c += 1
        prev = kind
        shots.append(shot_for(kind, b["t0"], b["t1"], i))
    return shots


# ---- the world ----------------------------------------------------------------------------------------
def build(out=None):
    card = Card("turca")
    w = World(card)
    D = card.D
    comp = [(i, n) for i, n in enumerate(card.notes) if n["layer"] == "composer"]
    ev = lambda i, n: (n["t"], n["t"] + n["dur"], round(n["vel"] / 127 * 255), 0, 0, i)

    tile_rows = [[] for _ in range(60)]
    tooth_rows = [[] for _ in range(NT)]
    for i, n in comp:
        tile_rows[ring_of(n["pitch"]) * 12 + sector_of(n["pitch"] % 12)].append(ev(i, n))
        tooth_rows[n["pitch"] - PITCH0].append(ev(i, n))
    pins = make_pins(card)
    pin_rows = [[ev(i, card.notes[i]) for i in d["notes"]] for d in pins]
    t_tiles, t_teeth, t_pins = w.table(EventTable("tiles", tile_rows, D)), w.table(EventTable("teeth", tooth_rows, D)), w.table(EventTable("pins", pin_rows, D))
    names = band_names(card)

    # camera first, so the Viewpoint binds
    shots = shot_list(card)
    vp, ints, rts = W.camera_nodes(shots, D, fov=1.0)
    w.head.append(vp)
    w.add(*ints)
    w.routes += rts
    w.stats["interpolator_keys"] += sum(len(i.attrs["key"].split()) for i in ints)
    state_buses(w, card)

    # shaders (a Shape that shares one uses a USE)
    sh_floor = w.sh.make("ShFloor", "floor_vs", "floor_fs", [t_tiles.field(), ("u_key", "SFFloat", "inputOutput", 0), LAMP])
    sh_dome = w.sh.make("ShDome", "dome_vs", "dome_fs", [("u_key", "SFFloat", "inputOutput", 0), ("u_sec", "SFFloat", "inputOutput", 0), ("u_open", "SFFloat", "inputOutput", 0), ("u_qpm", "SFFloat", "inputOutput", QPM)])
    sh_hall = lambda: w.shared("ShHall", lambda: w.sh.make("ShHall", "hall_vs", "hall_fs", [("u_key", "SFFloat", "inputOutput", 0), ("u_lampI", "SFFloat", "inputOutput", 1.0)]))
    sh_barrel = metal_shader(w, "ShBarrel", 1.0, (1.0, 0.78, 0.42), 1.0, 1.0, albedo=BRONZE)
    sh_pins = metal_shader(w, "ShPins", 1.0, (1.0, 0.78, 0.42), 0.0, 1.0, "pins_vs", "pins_fs", [t_pins.field()], albedo=BRASS, flat=1.0)
    sh_halo = w.sh.make("ShHalo", "halo_vs", "halo_fs", [t_pins.field(), ("u_haloSize", "SFFloat", "inputOutput", 0.34)])
    sh_comb = metal_shader(w, "ShComb", 0.9, (0.85, 0.9, 1.0), 0.0, 1.0, "comb_vs", "comb_fs", [t_teeth.field()], albedo=STEEL, flat=1.0)
    sh_mount = metal_shader(w, "ShMount", 0.9, (1.0, 0.78, 0.42), 0.0, 1.0, albedo=BRASS)
    sh_lamp = w.sh.make("ShLantern", "lantern_vs", "lantern_fs", [("u_qpm", "SFFloat", "inputOutput", QPM)])
    sh_spr = w.sh.make("ShSprite", "sprite_vs", "sprite_fs", [("u_qpm", "SFFloat", "inputOutput", QPM)])
    w.routes += [route("KeyBus", "value_changed", "ShFloor", "u_key"), route("KeyBus", "value_changed", "ShDome", "u_key"), route("SectionBus", "value_changed", "ShDome", "u_sec"),
                 route("OpenBus", "value_changed", "ShDome", "u_open")]

    # the hall
    w.add(N("Transform", w.shape(dome_mesh(), sh_dome, solid=False, normals=False, color=False, attrs=False), translation=vec(0, DOME_Y, 0)))
    w.add(N("Group", N("TouchSensor", DEF="HoverTiles", description=""), w.shape(tiles_mesh(), sh_floor, solid=False, normals=False, color=False)))
    slab, wall = arcade_mesh()
    stone, brass = plinth_mesh()
    for mesh in (outer_floor(), hub_mesh(), slab, wall, stone, brass):
        w.add(w.shape(mesh, sh_hall(), solid=False))
    # the machine
    pm, hm = pins_mesh(pins, len(names))
    w.add(w.shape(comb_mesh(), sh_comb, solid=False, normals=False, color=False), w.shape(comb_mount(), sh_mount, solid=False, color=False))
    w.add(N("Transform", N("TouchSensor", DEF="HoverPins", description=""), w.shape(barrel_mesh(len(names)), sh_barrel, solid=False, color=False), w.shape(pm, sh_pins, solid=False, normals=False, color=False),
            w.shape(hm, sh_halo, blend=True, solid=False, normals=False, color=False, fx="Fx_Halo"),
            DEF="Barrel", translation=vec(-band_x(names.index(card.passes[0]["id"]), len(names)), BARREL_Y, BARREL_Z), rotation=vec(1, 0, 0, 0)))
    barrel_motion(w, card, names)
    # lanterns and the band
    lf, ls = lantern_meshes()
    w.add(w.shape(lf, sh_lamp, solid=False), w.shape(ls, sh_spr, blend=True, solid=False, normals=False, fx="Fx_Flares"))
    w.add(*automata_nodes(w, card))

    # what each row of each table means, for the page's hover and the Score witness (every drawn id is a card note; every composer note is drawn)
    drawn = dict(
        tiles=[[e[5] for e in r] for r in t_tiles.rows], teeth=[[e[5] for e in r] for r in t_teeth.rows],
        pins=[dict(src=d["src"], band=names[d["band"]], notes=d["notes"], x=round(band_x(d["band"], len(names)) + (d["pitch"] - (PITCH0 + PITCH1) // 2) * LANE, 5),
                   th=round(d["theta"], 5), dp=round(max(d["dpsi"], 0.014 / BARREL_R), 5)) for d in pins],
        floor=dict(r0=FLOOR_R0, r1=FLOOR_R1, rings=5, sectors=12, pitch0=36), pin_w=PIN_W, barrel_r=BARREL_R, intangible=list(w.intangible))
    extra = dict(pins=len(pins), bands=names, tiles=60, teeth=NT, composer_notes=len(comp), automata=[a[0] for a in AUTOMATA], shots=len(shots))
    rep = W.write_world(w, "Rondo alla Turca: the pinned barrel", "Every composer note is a pin, a comb tooth and a floor tile; the arrangement drives the clockwork band.", extra, background=(0.01, 0.015, 0.03), out=out)
    import json
    with open(os.path.join(out or W.OUT, "turca.map.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(drawn, separators=(",", ":")) + "\n")
    return rep


if __name__ == "__main__":
    r = build()
    print({k: v for k, v in r.items() if k not in ("tables", "bands")})
    print("tables", r["tables"])
