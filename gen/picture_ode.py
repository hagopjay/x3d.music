#!/usr/bin/env python3
"""The Ode tapestry's picture, 256 warp threads by 384 weft rows, as five print separations (spec: the weave rule, the picture).

"Freude, schöner Götterfunken": a radiant spark rising over a landscape, with linked silhouettes along the horizon. No faces, no text. Every cell is one of five threads or the bare linen:
    1 indigo (the dark: sky, ground, silhouettes)   laid by statement 1     2 silver (mist, hills, far rays)   laid by statement 2
    3 gold (halo, rays, horizon glow, river)        laid by statement 3     4 ivory (core, star, stars, ripples) and 5 crimson (warp accents) laid by statement 4
and a tone 0..31 that the shader turns into how bright the thread sits. A cell byte is  code | tone << 3  (code in bits 0 to 2). A later stage can swap in a generated candidate by
quantising it to the same five classes (quantize()); until then this procedural picture stands in (spec fallback), so the world never waits on a paid image.
Deterministic: fixed seeds, no clocks.
"""
import math
import numpy as np
from PIL import Image

CW, CH = 256, 384
SS = 3
LINEN, INDIGO, SILVER, GOLD, IVORY, CRIMSON = range(6)
NAMES = ["linen", "indigo", "silver", "gold", "ivory", "crimson"]
PALETTE = [(222, 210, 184), (44, 52, 142), (196, 204, 220), (238, 184, 74), (248, 240, 218), (204, 34, 52)]


def _grids():
    xs = (np.arange(CW * SS) + 0.5) / SS
    ys = (np.arange(CH * SS) + 0.5) / SS
    return np.meshgrid(xs, ys)


def ridge_far(x):
    return 252.0 + 7.0 * np.sin(x / 29.0 + 0.4) + 4.0 * np.sin(x / 11.0 + 1.1)


def ridge_near(x):
    return 276.0 + 9.0 * np.sin(x / 37.0 + 1.7) + 5.0 * np.sin(x / 15.0 + 0.2)


class Layers:
    def __init__(self):
        self.X, self.Y = _grids()
        self.cls = np.zeros(self.X.shape, np.uint8)
        self.tone = np.zeros(self.X.shape, np.float32)

    def paint(self, mask, cls, tone):
        self.cls[mask] = cls
        self.tone[mask] = np.broadcast_to(np.asarray(tone, np.float32), self.X.shape)[mask]

    def shape(self, draw_fn):
        """A boolean mask from PIL drawing in cell units."""
        from PIL import ImageDraw
        im = Image.new("L", (CW * SS, CH * SS), 0)
        d = ImageDraw.Draw(im)
        draw_fn(d, lambda p: [(x * SS, y * SS) for x, y in p])
        return np.asarray(im) > 0


def build():
    L = Layers()
    X, Y = L.X, L.Y
    rng = np.random.RandomState(20261101)
    sx, sy = 128.0, 168.0
    rf, rn = ridge_far(X), ridge_near(X)
    r = np.hypot(X - sx, Y - sy)
    ang = np.arctan2(Y - sy, X - sx)

    # the sky, darkest at the top and lightening toward the horizon
    sky = Y < rf
    L.paint(sky, INDIGO, 0.10 + 0.55 * np.clip(Y / 250.0, 0, 1) ** 1.5)
    # the glow along the horizon
    glow = sky & (Y > rf - 30)
    L.paint(glow, GOLD, 0.95 * np.clip(1 - (rf - Y) / 30.0, 0, 1) ** 1.4)
    # the halo round the spark, ringed in silver
    L.paint(sky & (r < 52), GOLD, 0.15 + 0.85 * np.clip(1 - r / 52.0, 0, 1) ** 1.1)
    L.paint(sky & (r >= 52) & (r < 58), SILVER, 0.75)
    # sixteen rays: the long ones gold, the short ones silver
    for k in range(16):
        axis = k * math.pi / 8 + math.pi / 16
        da = np.abs((ang - axis + math.pi) % (2 * math.pi) - math.pi)
        reach = 360.0 if k % 2 == 0 else 150.0
        half = 0.075 * np.clip(1 - r / reach, 0, 1) + 0.010
        m = sky & (r > 58) & (r < reach) & (da < half)
        L.paint(m, GOLD if k % 2 == 0 else SILVER, 0.95 * np.clip(1 - r / reach, 0, 1) ** 0.8 + 0.1)
    # the far hills, silver mist that is lightest at the crest
    far = (Y >= rf) & (Y < rn)
    L.paint(far, SILVER, 0.18 + 0.55 * np.clip(1 - (Y - rf) / np.maximum(rn - rf, 1), 0, 1) ** 1.3)
    # the near ground, deep indigo
    near = Y >= rn
    L.paint(near, INDIGO, 0.06 + 0.12 * (0.5 + 0.5 * np.sin(X / 6.0 + Y / 9.0)))
    # the river under the spark: a gold wedge ripple-banded in ivory
    half = 5.0 + 0.24 * np.maximum(Y - rn, 0)
    river = near & (Y > rn + 4) & (np.abs(X - sx) < half)
    L.paint(river, GOLD, 0.45 + 0.4 * (0.5 + 0.5 * np.cos(Y * 0.7)) * np.clip(1 - np.abs(X - sx) / half, 0, 1))
    ripple = river & (np.abs((Y - rn) % 9.0 - 4.5) < 0.9) & (np.abs(X - sx) < 0.6 * half)
    L.paint(ripple, IVORY, 0.8)
    # thirteen silhouettes along the near ridge, hand in hand
    xs = [16.0 + i * 224.0 / 12 for i in range(13)]
    yb = [float(ridge_near(np.float64(x))) + 1.5 for x in xs]

    def figures(d, P):
        for i, (x, y) in enumerate(zip(xs, yb)):
            d.ellipse([(x - 3.4) * SS, (y - 32.4) * SS, (x + 3.4) * SS, (y - 25.6) * SS], fill=255)
            d.polygon(P([(x - 4.6, y - 24.5), (x + 4.6, y - 24.5), (x + 4.0, y - 10), (x - 4.0, y - 10)]), fill=255)
            d.polygon(P([(x - 4.0, y - 10), (x - 0.4, y - 10), (x - 1.0, y), (x - 4.3, y)]), fill=255)
            d.polygon(P([(x + 0.4, y - 10), (x + 4.0, y - 10), (x + 4.3, y), (x + 1.0, y)]), fill=255)
            if i + 1 < len(xs):
                x2, y2 = xs[i + 1], yb[i + 1]
                p0, p1 = (x + 4.4, y - 22.0), (x2 - 4.4, y2 - 22.0)
                mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 - 4.0)
                d.line(P([p0, mid, p1]), fill=255, width=int(2.4 * SS))
            if i == 0:
                d.line(P([(x - 4.4, y - 22.0), (x - 9.5, y - 28.0)]), fill=255, width=int(2.4 * SS))
            if i == len(xs) - 1:
                d.line(P([(x + 4.4, y - 22.0), (x + 9.5, y - 28.0)]), fill=255, width=int(2.4 * SS))
    L.paint(L.shape(figures), INDIGO, 0.02)
    # the spark: a four-pointed and an eight-pointed star in ivory over a core
    def star(d, P):
        for ln, wd in ((92, 3.6), (58, 2.4)):
            for q in range(4):
                a = q * math.pi / 2 + (0.0 if ln == 92 else math.pi / 4)
                tip = (sx + ln * math.cos(a), sy + ln * math.sin(a))
                px, py = -math.sin(a) * wd, math.cos(a) * wd
                d.polygon(P([(sx + px, sy + py), tip, (sx - px, sy - py)]), fill=255)
    L.paint(L.shape(star), IVORY, 0.95)
    L.paint(r < 14.5, IVORY, 1.0)
    L.paint((r > 19) & (r < 21.5) & sky, IVORY, 0.7)
    # stars in the upper sky
    for _ in range(80):
        px, py = rng.uniform(8, 248), rng.uniform(8, 150)
        if math.hypot(px - sx, py - sy) < 70:
            continue
        s = 0.6 if rng.rand() < 0.7 else 1.3
        L.paint((np.abs(X - px) < s) & (np.abs(Y - py) < s), IVORY, 0.5 + 0.5 * rng.rand())
    # the frame, and the crimson accents on the warp: two border threads and a row of short ones in the foreground
    frame = (X < 5) | (X >= CW - 5) | (Y < 5) | (Y >= CH - 5)
    L.paint(frame, INDIGO, 0.03)
    L.paint((np.abs(X - 7.5) < 0.5) | (np.abs(X - (CW - 7.5)) < 0.5), CRIMSON, 0.9)
    for k in range(13):
        cx = 20.5 + k * 18.0                  # half-integer centres put each thread inside one cell column
        L.paint((np.abs(X - cx) < 0.5) & (Y > rn + 18) & (Y < CH - 12), CRIMSON, 0.85)
    return L


def cells(L=None):
    """(384, 256) uint8: the class and tone of every cell, by majority vote over the supersampled pixels."""
    L = L or build()
    c = L.cls.reshape(CH, SS, CW, SS).transpose(0, 2, 1, 3).reshape(CH, CW, SS * SS)
    t = L.tone.reshape(CH, SS, CW, SS).transpose(0, 2, 1, 3).reshape(CH, CW, SS * SS)
    counts = np.stack([(c == k).sum(axis=2) for k in range(6)], axis=2)
    cls = counts.argmax(axis=2)
    win = (c == cls[:, :, None])
    tone = (t * win).sum(axis=2) / np.maximum(win.sum(axis=2), 1)
    return (cls.astype(np.uint8) | (np.clip(np.round(tone * 31), 0, 31).astype(np.uint8) << 3)).astype(np.uint8)


def quantize(rgb):
    """A generated candidate (H x W x 3 uint8, any size) to the same cell bytes: resize to 256 x 384, nearest of the five thread colours, tone from the distance to it."""
    im = Image.fromarray(np.asarray(rgb, np.uint8)).resize((CW, CH), Image.LANCZOS)
    a = np.asarray(im, float)
    pal = np.array(PALETTE[1:], float)
    d = np.linalg.norm(a[:, :, None, :] - pal[None, None, :, :], axis=3)
    k = d.argmin(axis=2)
    lum = a.mean(axis=2) / 255.0
    return ((k + 1).astype(np.uint8) | (np.clip(np.round(lum * 31), 0, 31).astype(np.uint8) << 3)).astype(np.uint8)


def preview(path, cell_bytes=None, scale=2):
    """The picture as the finished tapestry would look with every thread laid, as a PNG."""
    cb = cells() if cell_bytes is None else cell_bytes
    cls, tone = (cb & 7).astype(int), (cb >> 3) / 31.0
    pal = np.array(PALETTE, float)
    img = pal[cls] * (0.35 + 0.85 * tone[:, :, None])
    img = np.clip(img, 0, 255).astype(np.uint8)
    Image.fromarray(img).resize((CW * scale, CH * scale), Image.NEAREST).save(path)


def pack3(cb):
    """Three cell bytes per texel (R, G, B), 86 texels a row: the rows of the cells texture, as lists of (r, g, b)."""
    w = -(-CW // 3)
    pad = np.zeros((CH, w * 3), np.uint8)
    pad[:, :CW] = cb
    return pad.reshape(CH, w, 3), w


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ode_picture.png"
    cb = cells()
    preview(out, cb)
    print("class counts", {NAMES[k]: int(((cb & 7) == k).sum()) for k in range(6)}, "->", out)
