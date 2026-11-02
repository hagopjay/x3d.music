#!/usr/bin/env python3
"""Tests for the Ode world: the weave is score-true (every cell's owner is a note that sounds at the moment its row is woven, a gap is a real gap), every note of the card is one hole of the
card chain at the place and time it has in the score, the chain moves with the tempo map, the rose window is the circle of fifths, and the document is sane. Builds into a temp folder."""
import json, math, os, sys, tempfile, unittest
import xml.etree.ElementTree as ET
from fractions import Fraction as Fr
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import worldlib as W            # noqa: E402
import world_ode as O           # noqa: E402
import picture_ode as PIC       # noqa: E402

TMP = tempfile.mkdtemp(prefix="loomsong-ode-")
REPORT = O.build(out=TMP)
ROOT = ET.parse(os.path.join(TMP, "ode.x3d")).getroot()
with open(os.path.join(TMP, "ode.map.json"), encoding="utf-8") as _f:
    MAP = json.load(_f)
CARD = W.Card("ode")
RES = 1.5 * CARD.D / W.T24


def textures():
    out = {}
    for e in ROOT.iter("PixelTexture"):
        if e.get("DEF"):
            w, h, comp, *tx = e.get("image").split()
            out[e.get("DEF")[4:]] = (int(w), int(h), [int(x, 16) for x in tx])
    return out


TEX = textures()


def read_row(name, row):
    w, h, tx = TEX[name]
    v24 = lambda i: (tx[i] >> 8) & 0xFFFFFF
    base, first, n = v24(0), v24(1 + 2 * row), v24(2 + 2 * row)
    out = []
    for i in range(n):
        k = base + 4 * (first + i)
        out.append((v24(k) / 16777215 * CARD.D, v24(k + 1) / 16777215 * CARD.D, (tx[k + 2] >> 8) & 255, v24(k + 3)))
    return out


class Weave(unittest.TestCase):
    def test_the_owner_hash_spreads_cells_evenly_and_matches_its_published_vectors(self):
        """hash2u is the same 32-bit arithmetic in the shader and the page; the vectors in the map are what the page's own copy is checked against."""
        self.assertEqual(O.owner_hash(0, 0), 0)
        for n in (2, 3, 6):
            counts = [0] * n
            for x in range(0, 256, 3):
                for y in range(0, 384, 3):
                    counts[O.owner_hash(x, y) % n] += 1
            m = sum(counts) / n
            self.assertLess(max(abs(c - m) for c in counts) / m, 0.06, (n, counts))
        self.assertEqual({tuple(v) for v in MAP["hash"]}, {(x, y, O.owner_hash(x, y)) for x, y, _ in MAP["hash"]})

    def test_every_owner_sounds_at_the_moment_its_row_is_woven(self):
        n_events = 0
        for li, L in enumerate(O.LAYERS):
            for r in range(O.ROWS):
                tw = O.weave_time(CARD, li, r)
                evs = read_row("weave", li * O.ROWS + r)
                self.assertLessEqual(len(evs), O.MAX_CAND)
                self.assertEqual([e[0] for e in evs], sorted(e[0] for e in evs))
                for on, off, kind, nid in evs:
                    n = CARD.notes[nid]
                    self.assertIn(n["inst"], L["insts"], (L["name"], r, n["id"]))
                    self.assertLessEqual(on, tw + RES, (L["name"], r))
                    self.assertGreaterEqual(off, tw - RES, (L["name"], r))
                    self.assertAlmostEqual(on, n["t"], delta=RES)
                    self.assertAlmostEqual(off, n["t"] + n["dur"], delta=RES)
                    n_events += 1
        self.assertGreater(n_events, 3000)

    def test_a_row_is_bare_only_when_no_note_of_its_families_sounds_then(self):
        for li, L in enumerate(O.LAYERS):
            notes = [n for n in CARD.notes if n["inst"] in L["insts"]]
            for r in range(0, O.ROWS, 3):
                if read_row("weave", li * O.ROWS + r):
                    continue
                tw = O.weave_time(CARD, li, r)
                self.assertFalse([n["id"] for n in notes if n["t"] <= tw <= n["t"] + n["dur"]], (L["name"], r))

    def test_the_sweeps_are_the_statements_and_cover_rows_zero_to_383(self):
        a, b = O.sweep_vectors(CARD)
        for k, sec in enumerate(("S1", "S2", "S3", "S4")):
            p = next(p for p in CARD.passes if p["id"] == sec)
            self.assertAlmostEqual(a[k], p["t0"], places=6)
            self.assertAlmostEqual(b[k], p["t1"], places=6)
            self.assertAlmostEqual(O.weave_time(CARD, k, 0), p["t0"] + 0.5 / 384 * (p["t1"] - p["t0"]), places=6)
            self.assertAlmostEqual(O.weave_time(CARD, k, 383), p["t1"] - 0.5 / 384 * (p["t1"] - p["t0"]), places=6)
        self.assertEqual(O.LAYERS[3]["sec"], O.LAYERS[4]["sec"])                           # ivory and crimson are laid together, in the tutti

    def test_the_picture_is_read_back_from_the_file(self):
        w, h, tx = TEX["cells"]
        self.assertEqual((w, h), (86, 384))
        cb = PIC.cells()
        for r in (0, 100, 191, 383):
            for c in (0, 1, 2, 127, 255):
                texel = tx[r * w + c // 3]
                byte = (texel >> (24 - 8 * (c % 3))) & 255
                self.assertEqual(byte, int(cb[r, c]), (r, c))

    def test_every_thread_class_appears_and_every_cell_has_a_valid_class(self):
        cb = PIC.cells()
        cls = cb & 7
        self.assertTrue(set(np.unique(cls)) <= set(range(6)))
        for k in range(1, 6):
            self.assertGreater(int((cls == k).sum()), 300, PIC.NAMES[k])

    def test_how_much_of_each_separation_gets_woven(self):
        """The share of a layer's cells whose row has an owner: the rest stay bare linen, as the spec's sparse passages should."""
        cb = PIC.cells()
        for li, L in enumerate(O.LAYERS):
            rows = np.array([len(read_row("weave", li * O.ROWS + r)) > 0 for r in range(O.ROWS)])
            cells = (cb & 7) == li + 1
            share = float(cells[rows].sum()) / max(int(cells.sum()), 1)
            print("  %-8s rows with an owner %3d of 384, cells woven %.0f%%" % (L["name"], int(rows.sum()), 100 * share))
            if L["name"] != "crimson":
                self.assertGreater(share, 0.9, L["name"])


class Cards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mesh = O.belt_mesh(CARD)
        a = cls.mesh.attrs
        cls.kind, cls.nid, cls.t0, cls.t1, cls.loc = a["kind"][:, 0], a["id"][:, 0], a["t0"][:, 0], a["t1"][:, 0], a["loc"]

    def test_every_note_is_exactly_one_hole(self):
        ids = self.nid[self.kind > 0.5].astype(int)
        self.assertEqual(len(ids), 4 * len(CARD.notes))
        counts = np.bincount(ids, minlength=len(CARD.notes))
        self.assertTrue((counts == 4).all())
        comp = {i for i, n in enumerate(CARD.notes) if n["layer"] == "composer"}
        self.assertTrue(comp <= set(ids.tolist()))
        self.assertEqual(len(comp), 327)

    def test_a_hole_starts_in_its_card_where_the_note_starts_in_its_beat_and_carries_the_notes_times(self):
        sel = np.where(self.kind > 0.5)[0]
        for v in sel[::4]:
            i = int(self.nid[v])
            n = CARD.notes[i]
            xs = self.loc[v:v + 4, 0]
            self.assertAlmostEqual(xs.min(), O.CARD_P * float(Fr(n["q"])), places=6, msg=n["id"])
            self.assertAlmostEqual(self.t0[v], n["t"], places=6)
            self.assertAlmostEqual(self.t1[v], n["t"] + n["dur"], places=6)
            self.assertEqual(int(math.floor(xs.min() / O.CARD_P + 1e-9)), int(math.floor(float(Fr(n["q"])) + 1e-9)))     # card k holds the notes that begin in beat k

    def test_lanes_cover_every_instrument_and_keep_holes_inside_the_card(self):
        self.assertTrue({n["inst"] for n in CARD.notes} <= set(O.LANES))
        sel = self.kind > 0.5
        ys = self.loc[sel, 1]
        self.assertTrue((ys > -1.0).all() and (ys < 1.0).all())

    def test_the_chain_moves_one_card_a_beat_and_a_hole_is_at_the_reading_bar_when_its_note_starts(self):
        bt, bp = O.belt_keys(CARD)
        bx = [p[0] for p in bp]
        worst = 0.0
        for n in CARD.notes[::7]:
            x = O.CARD_P * float(Fr(n["q"])) + float(np.interp(n["t"], bt, bx))
            worst = max(worst, abs(x))
        self.assertLess(worst, 0.0015, "a hole is %.4f m from the reading bar when its note starts" % worst)
        for t in np.linspace(1, CARD.seconds - 1, 300):
            self.assertAlmostEqual(-float(np.interp(t, bt, bx)) / O.CARD_P, CARD.t_q(float(t)), delta=0.012)


class Window(unittest.TestCase):
    def test_the_rose_window_rows_are_the_circle_of_fifths(self):
        n = 0
        for k, h in enumerate(CARD.harmony):
            for pc in h["pcs"]:
                evs = read_row("chords", (pc * 7) % 12)
                match = [e for e in evs if e[3] == k]
                self.assertEqual(len(match), 1, (k, pc))
                self.assertAlmostEqual(match[0][0], h["t"], delta=RES)
                self.assertAlmostEqual(match[0][1], h["t"] + h["dur"], delta=RES)
                n += 1
        self.assertGreater(n, 300)

    def test_buses_stay_in_range(self):
        for name, f in (("act", O.activity_keys), ("tension", O.tension_keys)):
            ks, vs = f(CARD)
            self.assertTrue(all(b >= a for a, b in zip(ks, ks[1:])), name)
            self.assertTrue(min(vs) >= 0.0 and max(vs) <= 1.0, (name, min(vs), max(vs)))


class Loom(unittest.TestCase):
    def test_the_weave_line_stands_at_the_row_being_woven(self):
        ct, cy = O.carriage_keys(CARD)
        for li in range(4):
            for r in (0, 50, 200, 383):
                tw = O.weave_time(CARD, li, r)
                want = O.TAP_TOP - (O.TAP_TOP - O.TAP_BOT) * (r + 0.5) / O.ROWS
                self.assertAlmostEqual(float(np.interp(tw, ct, cy)), want, delta=0.01, msg=(li, r))

    def test_the_shuttle_arrives_on_every_melody_note(self):
        sk, sx = O.shuttle_keys(CARD)
        ons = sorted({n["t"] for n in CARD.composer()})
        for t in ons:
            self.assertAlmostEqual(abs(float(np.interp(t, sk, sx))), O.SHUTTLE_X, delta=1e-3, msg=t)

    def test_the_batten_beats_on_every_kick_and_snare_and_the_harness_lifts_on_every_hat(self):
        for insts, rest, hit in ((("kick", "snare"), 0.0, -0.32), (("hat",), 0.0, O.HIT_Y)):
            ts = sorted({n["t"] for n in CARD.notes if n["inst"] in insts})
            ks, vs = O.hit_keys(ts, rest, hit, CARD.D)
            self.assertTrue(all(b > a for a, b in zip(ks, ks[1:])))
            ok = sum(1 for t in ts if abs(float(np.interp(t, ks, vs)) - hit) < 1e-6)
            self.assertGreater(ok / len(ts), 0.97, insts)                                  # a crowded event may be thinned out, never moved


class Camera(unittest.TestCase):
    def test_twelve_shots_and_cuts_on_the_statement_changes(self):
        shots = O.shot_list(CARD)
        self.assertEqual(len(shots), 12)
        starts = {round(s.t0, 3) for s in shots}
        for p in CARD.passes:
            self.assertIn(round(p["t0"], 3), starts, p["id"])


class Document(unittest.TestCase):
    def test_interpolator_keys_increase_and_stay_in_range(self):
        n = 0
        for e in ROOT.iter():
            if e.tag.endswith("Interpolator") and e.get("key"):
                k = [float(x) for x in e.get("key").split()]
                self.assertTrue(all(b > a for a, b in zip(k, k[1:])), e.get("DEF"))
                self.assertTrue(0.0 <= k[0] and k[-1] <= 1.0, e.get("DEF"))
                n += 1
        self.assertGreater(n, 12)

    def test_every_route_names_nodes_that_exist(self):
        defs = {e.get("DEF"): e for e in ROOT.iter() if e.get("DEF")}
        routes = list(ROOT.iter("ROUTE"))
        self.assertGreater(len(routes), 40)
        for r in routes:
            self.assertIn(r.get("fromNode"), defs)
            self.assertIn(r.get("toNode"), defs)

    def test_every_shader_is_wired_to_the_bus_and_declares_the_standard_fields(self):
        routed = {r.get("toNode") for r in ROOT.iter("ROUTE") if r.get("fromNode") == "SecondsBus" and r.get("toField") == "u_time"}
        for sh in ROOT.iter("ComposedShader"):
            if sh.get("DEF"):
                self.assertIn(sh.get("DEF"), routed)
                self.assertTrue({"u_time", "u_dur", "u_idpass", "u_calm"} <= {f.get("name") for f in sh.iter("field")}, sh.get("DEF"))

    def test_budgets(self):
        self.assertLessEqual(REPORT["draw_calls"], 150)
        self.assertLessEqual(REPORT["triangles"], 1_500_000)
        self.assertLessEqual(REPORT["texture_bytes"], 512 * 1024 * 1024)
        self.assertLess(REPORT["bytes"], 16 * 1024 * 1024)

    def test_same_inputs_same_bytes(self):
        d2 = tempfile.mkdtemp(prefix="loomsong-ode2-")
        O.build(out=d2)
        with open(os.path.join(TMP, "ode.x3d"), "rb") as f:
            a = f.read()
        with open(os.path.join(d2, "ode.x3d"), "rb") as f:
            b = f.read()
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
