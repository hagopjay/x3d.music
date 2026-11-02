"""Small deterministic mesh library for the world generators: primitives, transforms, merging, baked light, and the X3D nodes that carry a mesh.

Everything is numpy arrays and fixed seeds, so the same inputs give the same bytes. A Mesh is an indexed triangle list with per-vertex position, normal and colour (colour is where
static light is baked) plus any number of extra per-vertex attributes (note id, tile index, ...) that become FloatVertexAttribute nodes. Y is up, the camera looks down -Z, units are metres.
"""
import math
import numpy as np

from x3dw import N, mf


# ---- transforms ---------------------------------------------------------------------------------
def T(x=0.0, y=0.0, z=0.0):
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


def S(x=1.0, y=None, z=None):
    y = x if y is None else y
    z = x if z is None else z
    return np.diag([x, y, z, 1.0])


def R(axis, angle):
    """Rotation by `angle` radians about a unit-length-normalised axis (right-handed)."""
    a = np.asarray(axis, dtype=float)
    a = a / np.linalg.norm(a)
    c, s = math.cos(angle), math.sin(angle)
    x, y, z = a
    m = np.eye(4)
    m[:3, :3] = [[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                 [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                 [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]]
    return m


def compose(*ms):
    """compose(A, B, C) applies C first, then B, then A (the matrix product A @ B @ C)."""
    out = np.eye(4)
    for m in ms:
        out = out @ m
    return out


def look_rotation(eye, target, up=(0.0, 1.0, 0.0)):
    """The X3D SFRotation (x, y, z, angle) that turns the default view direction (-Z, up +Y) toward `target` from `eye`."""
    f = np.asarray(target, float) - np.asarray(eye, float)
    f = f / np.linalg.norm(f)
    r = np.cross(f, np.asarray(up, float))
    if np.linalg.norm(r) < 1e-9:                                   # looking straight along the up axis
        r = np.array([1.0, 0.0, 0.0])
    r = r / np.linalg.norm(r)
    u = np.cross(r, f)
    m = np.array([r, u, -f]).T                                      # columns: camera right, up, back, in world axes
    return matrix_to_axis_angle(m)


def matrix_to_axis_angle(m):
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    angle = math.acos(max(-1.0, min(1.0, (tr - 1) / 2)))
    if angle < 1e-9:
        return (0.0, 1.0, 0.0, 0.0)
    if abs(angle - math.pi) < 1e-6:                                 # 180 degrees: read the axis from the diagonal
        i = int(np.argmax(np.diag(m)))
        v = np.sqrt(np.maximum((np.diag(m) + 1) / 2, 0))
        v[i] = max(v[i], 1e-9)
        for j in range(3):
            if j != i:
                v[j] = math.copysign(v[j], m[i, j] + m[j, i])
        v = v / np.linalg.norm(v)
        return (float(v[0]), float(v[1]), float(v[2]), math.pi)
    axis = np.array([m[2, 1] - m[1, 2], m[0, 2] - m[2, 0], m[1, 0] - m[0, 1]]) / (2 * math.sin(angle))
    axis = axis / np.linalg.norm(axis)
    return (float(axis[0]), float(axis[1]), float(axis[2]), float(angle))


# ---- the mesh -----------------------------------------------------------------------------------
class Mesh:
    def __init__(self, P=None, Nrm=None, F=None, C=None, attrs=None):
        self.P = np.zeros((0, 3)) if P is None else np.asarray(P, float).reshape(-1, 3)
        self.N = np.zeros((0, 3)) if Nrm is None else np.asarray(Nrm, float).reshape(-1, 3)
        self.F = np.zeros((0, 3), dtype=np.int64) if F is None else np.asarray(F, dtype=np.int64).reshape(-1, 3)
        self.C = np.ones((len(self.P), 3)) if C is None else np.asarray(C, float).reshape(-1, 3)
        self.attrs = {k: np.asarray(v, float).reshape(len(self.P), -1) for k, v in (attrs or {}).items()}

    def __len__(self):
        return len(self.P)

    def copy(self):
        return Mesh(self.P.copy(), self.N.copy(), self.F.copy(), self.C.copy(), {k: v.copy() for k, v in self.attrs.items()})

    def transformed(self, m):
        m = np.asarray(m, float)
        P = self.P @ m[:3, :3].T + m[:3, 3]
        nm = np.linalg.inv(m[:3, :3]).T
        Nn = self.N @ nm.T
        ln = np.linalg.norm(Nn, axis=1, keepdims=True)
        Nn = Nn / np.where(ln > 1e-12, ln, 1.0)
        return Mesh(P, Nn, self.F, self.C, self.attrs)

    def colored(self, rgb):
        return Mesh(self.P, self.N, self.F, np.tile(np.asarray(rgb, float), (len(self.P), 1)), self.attrs)

    def with_attr(self, name, value):
        a = dict(self.attrs)
        v = np.asarray(value, float)
        a[name] = np.tile(v.reshape(1, -1), (len(self.P), 1)) if v.size and v.ndim <= 1 else v.reshape(len(self.P), -1)
        return Mesh(self.P, self.N, self.F, self.C, a)

    @property
    def triangles(self):
        return len(self.F)


def merge(meshes):
    """One mesh from many. Every mesh must carry the same attribute names; a missing one is filled with zeros."""
    meshes = [m for m in meshes if len(m)]
    if not meshes:
        return Mesh()
    names = sorted({k for m in meshes for k in m.attrs})
    widths = {k: next(m.attrs[k].shape[1] for m in meshes if k in m.attrs) for k in names}
    P, Nn, F, C, A, base = [], [], [], [], {k: [] for k in names}, 0
    for m in meshes:
        P.append(m.P); Nn.append(m.N); C.append(m.C); F.append(m.F + base); base += len(m.P)
        for k in names:
            A[k].append(m.attrs[k] if k in m.attrs else np.zeros((len(m.P), widths[k])))
    return Mesh(np.vstack(P), np.vstack(Nn), np.vstack(F), np.vstack(C), {k: np.vstack(v) for k, v in A.items()})


def _flat(quads_or_tris):
    """Build a Mesh from a list of planar polygons (each a list of 3D points, counter-clockwise seen from outside), with a flat normal per polygon."""
    P, Nn, F = [], [], []
    for poly in quads_or_tris:
        p = np.asarray(poly, float)
        n = np.cross(p[1] - p[0], p[2] - p[0])
        ln = np.linalg.norm(n)
        n = n / ln if ln > 1e-12 else np.array([0.0, 1.0, 0.0])
        b = len(P)
        P.extend(p.tolist()); Nn.extend([n.tolist()] * len(p))
        for i in range(1, len(p) - 1):
            F.append([b, b + i, b + i + 1])
    return Mesh(P, Nn, F)


# ---- primitives ---------------------------------------------------------------------------------
def box(sx=1.0, sy=1.0, sz=1.0, center=(0.0, 0.0, 0.0)):
    x, y, z = sx / 2, sy / 2, sz / 2
    c = np.asarray(center, float)
    quads = [[(x, -y, -z), (x, y, -z), (x, y, z), (x, -y, z)], [(-x, -y, z), (-x, y, z), (-x, y, -z), (-x, -y, -z)],
             [(-x, y, -z), (-x, y, z), (x, y, z), (x, y, -z)], [(-x, -y, z), (-x, -y, -z), (x, -y, -z), (x, -y, z)],
             [(-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)], [(x, -y, -z), (-x, -y, -z), (-x, y, -z), (x, y, -z)]]
    return _flat([[np.add(p, c) for p in q] for q in quads])


def lathe(profile, seg=24, smooth=True, closed_axis=False):
    """Surface of revolution about +Y from a polyline of (radius, y) pairs, bottom to top. Normals are smooth around the axis and follow the profile's slope."""
    pr = np.asarray(profile, float)
    n = len(pr)
    ang = np.linspace(0, 2 * math.pi, seg + 1)
    P, Nn = [], []
    for i in range(n):
        a, b = pr[max(i - 1, 0)], pr[min(i + 1, n - 1)]
        tr, ty = b[0] - a[0], b[1] - a[1]                           # tangent in (r, y); the outward normal is (ty, -tr)
        nr, ny = ty, -tr
        ln = math.hypot(nr, ny) or 1.0
        nr, ny = nr / ln, ny / ln
        for t in ang:
            P.append((pr[i][0] * math.cos(t), pr[i][1], pr[i][0] * math.sin(t)))
            Nn.append((nr * math.cos(t), ny, nr * math.sin(t)))
    F = []
    for i in range(n - 1):
        for j in range(seg):
            a, b = i * (seg + 1) + j, i * (seg + 1) + j + 1
            c, d = (i + 1) * (seg + 1) + j, (i + 1) * (seg + 1) + j + 1
            F += [[a, c, b], [b, c, d]]
    m = Mesh(P, Nn, F)
    if not smooth:
        m = _unsmooth(m)
    return m


def _unsmooth(m):
    return _flat([m.P[f] for f in m.F])


def cylinder(r0=0.5, r1=None, h=1.0, seg=16, caps=True, smooth=True):
    r1 = r0 if r1 is None else r1
    body = lathe([(r0, 0.0), (r1, h)], seg, smooth)
    if not caps:
        return body
    parts = [body]
    for r, y, up in ((r0, 0.0, False), (r1, h, True)):
        if r > 1e-9:
            parts.append(disc(r, seg, up).transformed(T(0, y, 0)))
    return merge(parts)


def disc(r=1.0, seg=24, up=True):
    P = [(0.0, 0.0, 0.0)] + [(r * math.cos(2 * math.pi * i / seg), 0.0, r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
    F = [[0, 1 + (i + 1) % seg, 1 + i] if up else [0, 1 + i, 1 + (i + 1) % seg] for i in range(seg)]
    return Mesh(P, [(0.0, 1.0 if up else -1.0, 0.0)] * len(P), F)


def sphere(r=1.0, seg=24, rings=12):
    prof = [(r * math.sin(math.pi * i / rings), -r * math.cos(math.pi * i / rings)) for i in range(rings + 1)]
    return lathe(prof, seg)


def torus(R_major=1.0, r_minor=0.2, seg=32, tube=12):
    P, Nn, F = [], [], []
    for i in range(seg + 1):
        u = 2 * math.pi * i / seg
        for j in range(tube + 1):
            v = 2 * math.pi * j / tube
            cx, cz = R_major * math.cos(u), R_major * math.sin(u)
            nx, ny, nz = math.cos(v) * math.cos(u), math.sin(v), math.cos(v) * math.sin(u)
            P.append((cx + r_minor * nx, r_minor * ny, cz + r_minor * nz)); Nn.append((nx, ny, nz))
    for i in range(seg):
        for j in range(tube):
            a, b = i * (tube + 1) + j, (i + 1) * (tube + 1) + j
            F += [[a, a + 1, b], [a + 1, b + 1, b]]
    return Mesh(P, Nn, F)


def ring_sector(r0, r1, a0, a1, seg=6, y=0.0, up=True):
    """A flat annular sector between radii r0 and r1 and angles a0..a1 (radians, measured from +X toward +Z), facing up (or down)."""
    angs = np.linspace(a0, a1, seg + 1)
    P = []
    for a in angs:
        P.append((r0 * math.cos(a), y, r0 * math.sin(a)))
        P.append((r1 * math.cos(a), y, r1 * math.sin(a)))
    F = []
    for i in range(seg):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3         # inner and outer corner at this angle, then at the next
        F += [[a, c, b], [b, c, d]] if up else [[a, b, c], [b, d, c]]
    return Mesh(P, [(0.0, 1.0 if up else -1.0, 0.0)] * len(P), F)


def arch_prism(width, height, depth, seg=12, thickness=0.0):
    """A solid slab with a round-topped (semicircular) opening: the outline of an arcade bay seen from +Z, extruded `depth` along Z. width and height are the opening's.
    Returned centred on x = 0 with its base at y = 0 and z from -depth/2 to +depth/2; the slab around it is `thickness` thick on each side."""
    w2 = width / 2
    rise = height - w2
    outer = w2 + thickness
    pts = [(-outer, 0.0), (-w2, 0.0)]
    pts += [(-w2, rise)] if rise > 0 else []
    for i in range(1, seg):
        a = math.pi - math.pi * i / seg
        pts.append((w2 * math.cos(a), rise + w2 * math.sin(a)))
    pts += [(w2, rise)] if rise > 0 else []
    pts += [(w2, 0.0), (outer, 0.0), (outer, height + thickness), (-outer, height + thickness)]
    return extrude_polygon(pts, depth)


def extrude_polygon(pts2, depth):
    """Extrude a simple 2D outline (x, y), listed counter-clockwise, along Z from -depth/2 to +depth/2. Concave outlines are fine: caps are triangulated by ear clipping."""
    pts2 = [tuple(p) for p in pts2]
    n = len(pts2)
    z0, z1 = -depth / 2, depth / 2
    quads = []
    for i in range(n):
        a, b = pts2[i], pts2[(i + 1) % n]
        quads.append([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)])
    side = _flat(quads)
    tris = _ear_clip(pts2)
    cap_front = _flat([[(pts2[i][0], pts2[i][1], z1) for i in t] for t in tris])
    cap_back = _flat([[(pts2[i][0], pts2[i][1], z0) for i in reversed(t)] for t in tris])
    return merge([side, cap_front, cap_back])


def _ear_clip(pts):
    idx = list(range(len(pts)))
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area < 0:
        idx.reverse()
    out = []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inside(p, a, b, c):
        return cross(a, b, p) >= -1e-12 and cross(b, c, p) >= -1e-12 and cross(c, a, p) >= -1e-12

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if cross(a, b, c) <= 1e-12:
                continue
            if any(inside(pts[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            out.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        out.append(tuple(idx))
    return out


# ---- light baked into vertex colour -------------------------------------------------------------
def bake(mesh, albedo=None, ambient=(0.05, 0.06, 0.09), sky=((0.02, 0.03, 0.06), (0.10, 0.12, 0.20)), lights=(), gain=1.0, ao=None):
    """Write lit colour into mesh.C: albedo * (hemisphere ambient + sum of point lights with Lambert and inverse-square falloff). Lights are (position, rgb, intensity, radius).
    `ao(P)` may return an array of 0..1 occlusion factors. Static light only; anything that moves is lit in its shader."""
    alb = mesh.C if albedo is None else np.tile(np.asarray(albedo, float), (len(mesh.P), 1))
    up = np.clip(mesh.N[:, 1:2] * 0.5 + 0.5, 0, 1)
    amb = np.asarray(sky[0], float) * (1 - up) + np.asarray(sky[1], float) * up + np.asarray(ambient, float)
    lit = amb.copy()
    for pos, rgb, inten, radius in lights:
        d = np.asarray(pos, float) - mesh.P
        dist = np.linalg.norm(d, axis=1, keepdims=True)
        l = d / np.maximum(dist, 1e-9)
        lam = np.clip(np.sum(l * mesh.N, axis=1, keepdims=True), 0, 1)
        att = inten / (1.0 + (dist / radius) ** 2) ** 2
        lit = lit + lam * att * np.asarray(rgb, float)
    if ao is not None:
        lit = lit * np.asarray(ao(mesh.P), float).reshape(-1, 1)
    return Mesh(mesh.P, mesh.N, mesh.F, np.clip(alb * lit * gain, 0, 4.0), mesh.attrs)


# ---- X3D ----------------------------------------------------------------------------------------
COLOR_GAIN = 0.5      # X3D colours live in 0..1 (the validator checks the range), so baked light is stored at half strength and every Loomsong shader doubles it back


def geometry(mesh, normals=True, color=True, attrs=True, places=3, solid=True, color_gain=COLOR_GAIN):
    """IndexedTriangleSet carrying the mesh. Extra attributes become FloatVertexAttribute nodes named `a_<name>`.
    Colour is written as clip(C * color_gain, 0, 1): baked light above 1 / color_gain is lost, so bake with that headroom in mind."""
    kids = [N("Coordinate", point=mf(mesh.P.reshape(-1), places, per=12))]
    if normals:
        kids.append(N("Normal", vector=mf(np.round(mesh.N, 2).reshape(-1), 2, per=12)))
    if color:
        kids.append(N("Color", color=mf(np.round(np.clip(mesh.C * color_gain, 0, 1), 3).reshape(-1), 3, per=12)))
    if attrs:
        for k in sorted(mesh.attrs):
            v = mesh.attrs[k]
            kids.append(N("FloatVertexAttribute", name="a_" + k, numComponents=v.shape[1], value=mf(v.reshape(-1), 4, per=12)))
    return N("IndexedTriangleSet", *kids, index=mf(mesh.F.reshape(-1).tolist(), 0, per=18), solid=solid)
