#!/usr/bin/env python3
"""Tests for the Turca world: the barrel really delivers every pin to the comb at its note's time, every composer note is drawn exactly once by each of the three elements, the event
tables read back from the file equal the card, and the interpolator keys are sane. Builds the world into a temporary folder (about a second)."""
import math, os, sys, tempfile, unittest
import xml.etree.ElementTree as ET
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import worldlib as W            # noqa: E402
import world_turca as T         # noqa: E402

TMP = tempfile.mkdtemp(prefix="loomsong-turca-")
REPORT = T.build(out=TMP)
TREE = ET.parse(os.path.join(TMP, "turca.x3d"))
ROOT = TREE.getroot()
CARD = W.Card("turca")
SPLIT = REPORT["pins"] - 1613          # written heads whose second statement lands on another band or angle get a pin of their own


def by_def(tag=None):
    return {e.get("DEF"): e for e in ROOT.iter() if e.get("DEF") and (tag is None or e.tag == tag)}


class Barrel(unittest.TestCase):
    def setUp(self):
        self.names = T.band_names(CARD)
        self.rt, self.rv, self.pt, self.pv = T.barrel_keys(CARD, self.names, CARD.D)
        self.pins = T.make_pins(CARD)

    def phi(self, t):
        return float(np.interp(t, self.rt, self.rv))

    def x(self, t):
        return float(np.interp(t, self.pt, [v[0] for v in self.pv]))

    def test_every_pin_meets_the_comb_at_its_note_time(self):
        worst, n = 0.0, 0
        for d in self.pins:
            psi0 = d["theta"]
            for i in d["notes"]:
                t = CARD.notes[i]["t"]
                err = (self.phi(t) - psi0 + math.pi) % (2 * math.pi) - math.pi       # apparent angle of the pin's leading edge when the note starts (0 = at the comb)
                worst = max(worst, abs(err)); n += 1
        self.assertEqual(n, 2810)
        self.assertLess(worst, 2e-3, "a pin's leading edge is %.4f rad off the comb at its note's time" % worst)

    def test_the_comb_tooth_is_under_the_pin_at_its_note_time(self):
        nb = len(self.names)
        worst = 0.0
        for d in self.pins:
            for i in d["notes"]:
                worst = max(worst, abs(T.band_x(d["band"], nb) + self.x(CARD.notes[i]["t"])))      # the barrel's offset must undo the band's offset, so the lane under the comb is the pin's pitch
        self.assertLess(worst, 1e-3, "a pin is %.4f m from its tooth when its note starts" % worst)

    def test_the_barrel_only_changes_band_in_silence(self):
        onsets = sorted(n["t"] for n in CARD.composer())
        wins = T.shift_windows(CARD, self.names)
        self.assertEqual(len(wins), 12)
        for depart, arrive, _ in wins:
            self.assertFalse([t for t in onsets if depart + 1e-9 < t < arrive - 1e-9], "a note sounds while the barrel slides")
        print("  band changes (ms): " + " ".join("%d" % round((a - d) * 1000) for d, a, _ in wins))

    def test_a_pin_touches_a_tooth_only_when_its_note_sounds(self):
        """Every time a pin comes round to the comb while the barrel is on its band, one of its notes sounds then; the exceptions are listed and counted."""
        nb = len(self.names)
        silent = []
        for d in self.pins:
            for m in range(int(math.ceil((self.rv[0] - d["theta"]) / T.TAU)), int(math.floor((self.rv[-1] - d["theta"]) / T.TAU)) + 1):
                tgt = d["theta"] + T.TAU * m
                if not (self.rv[0] <= tgt <= self.rv[-1]):
                    continue
                t = float(np.interp(tgt, self.rv, self.rt))
                if abs(T.band_x(d["band"], nb) + self.x(t)) > 0.4 * T.LANE:
                    continue                                        # the barrel is on another band: the pin goes by beside the comb
                if not any(abs(CARD.notes[i]["t"] - t) < 5e-3 for i in d["notes"]):
                    silent.append((round(t, 3), d["src"], CARD.notes[d["notes"][0]]["id"]))
        print("  silent crossings (pin meets a tooth, no note): %d %s" % (len(silent), silent))
        # the pickup graces of the second ending (I2) sound while the barrel is still on band I, so their pins sit on that band, which the first statement of I turns past as well
        self.assertLessEqual(len(silent), 3, silent)
        self.assertTrue({s_[1] for s_ in silent} <= {"811:1", "812:1", "813:1"}, silent)

    def test_one_full_turn_per_pass_and_the_last_stops_when_its_last_note_has_died(self):
        for p in CARD.passes[:-1]:
            self.assertAlmostEqual(self.phi(p["t1"]) - self.phi(p["t0"]), 2 * math.pi, places=2, msg=p["id"])
        last = CARD.passes[-1]
        turn = self.phi(last["t1"]) - self.phi(last["t0"])
        self.assertTrue(0.97 * 2 * math.pi < turn < 2 * math.pi, turn)

    def test_pins_are_the_written_heads_and_reps_reuse_them(self):
        self.assertEqual(len(self.pins), 1613 + SPLIT)
        self.assertEqual(max(len(d["notes"]) for d in self.pins), 2)
        ids = sorted(i for d in self.pins for i in d["notes"])
        self.assertEqual(ids, sorted(i for i, n in enumerate(CARD.notes) if n["layer"] == "composer"))

    def test_bands_in_order_of_first_appearance(self):
        self.assertEqual(self.names, ["A", "B", "C", "D", "E", "F", "G", "H", "I", "I1", "I2", "J"])


class Tables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tex = {}
        for e in ROOT.iter("PixelTexture"):
            if e.get("DEF"):
                w, h, comp, *tx = e.get("image").split()
                cls.tex[e.get("DEF")[4:]] = (int(w), int(h), [int(x, 16) for x in tx])
        cls.D = CARD.D

    def read(self, name, row):
        w, h, tx = self.tex[name]
        v24 = lambda i: (tx[i] >> 8) & 0xFFFFFF
        base, first, n = v24(0), v24(1 + 2 * row), v24(2 + 2 * row)
        out = []
        for i in range(n):
            k = base + 4 * (first + i)
            out.append((v24(k) / 16777215 * self.D, v24(k + 1) / 16777215 * self.D, v24(k + 3)))
        return out

    def test_alpha_is_always_opaque(self):
        for name, (w, h, tx) in self.tex.items():
            self.assertTrue(all((x & 255) == 255 for x in tx), name)

    def test_each_composer_note_is_drawn_once_by_a_tile_a_tooth_and_a_pin(self):
        comp = {i for i, n in enumerate(CARD.notes) if n["layer"] == "composer"}
        for name, rows in (("tiles", 60), ("teeth", T.NT), ("pins", 1613)):
            seen = [e[2] for r in range(rows) for e in self.read(name, r)]
            self.assertEqual(len(seen), len(comp), name)
            self.assertEqual(set(seen), comp, name)

    def test_event_times_equal_the_card_to_the_texture_resolution(self):
        res = 1.5 * self.D / 16777215
        for r in range(T.NT):
            for on, off, i in self.read("teeth", r):
                n = CARD.notes[i]
                self.assertEqual(n["pitch"] - T.PITCH0, r)
                self.assertAlmostEqual(on, n["t"], delta=res)
                self.assertAlmostEqual(off, n["t"] + n["dur"], delta=res)

    def test_tile_is_the_circle_of_fifths_by_pitch_class_and_the_octave_ring(self):
        for r in range(60):
            for on, off, i in self.read("tiles", r):
                p = CARD.notes[i]["pitch"]
                self.assertEqual(r, T.ring_of(p) * 12 + T.sector_of(p % 12))

    def test_rows_are_sorted_by_onset(self):
        for name, rows in (("tiles", 60), ("teeth", T.NT), ("pins", 1613)):
            for r in range(rows):
                ts = [e[0] for e in self.read(name, r)]
                self.assertEqual(ts, sorted(ts), (name, r))


class Document(unittest.TestCase):
    def test_interpolator_keys_increase_and_stay_in_range(self):
        n = 0
        for e in ROOT.iter():
            if e.tag.endswith("Interpolator") and e.get("key"):
                k = [float(x) for x in e.get("key").split()]
                self.assertTrue(all(b > a for a, b in zip(k, k[1:])), e.get("DEF"))
                self.assertTrue(0.0 <= k[0] and k[-1] <= 1.0, e.get("DEF"))
                n += 1
        self.assertGreater(n, 15)

    def test_every_route_names_nodes_that_exist(self):
        defs = by_def()
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
                fields = {f.get("name") for f in sh.iter("field")}
                self.assertTrue({"u_time", "u_dur", "u_idpass", "u_calm"} <= fields, sh.get("DEF"))

    def test_budgets(self):
        self.assertLessEqual(REPORT["draw_calls"], 150)
        self.assertLessEqual(REPORT["triangles"], 1_500_000)
        self.assertLessEqual(REPORT["texture_bytes"], 512 * 1024 * 1024)
        self.assertLess(REPORT["bytes"], 16 * 1024 * 1024)

    def test_same_inputs_same_bytes(self):
        d2 = tempfile.mkdtemp(prefix="loomsong-turca2-")
        T.build(out=d2)
        with open(os.path.join(TMP, "turca.x3d"), "rb") as f:
            a = f.read()
        with open(os.path.join(d2, "turca.x3d"), "rb") as f:
            b = f.read()
        self.assertEqual(a, b)


class Automata(unittest.TestCase):
    def test_every_score_event_of_a_band_instrument_is_one_strike_and_every_arm_that_moves_has_a_reason(self):
        """Each event of the instrument lands as a hit (the arm key at ARM_HIT) on the arm that plays it, at the event's own time; no arm is driven without an event."""
        card = W.Card("turca")
        by = {}
        for n in card.notes:
            by.setdefault(n["inst"], []).append(n["t"])
        ints = {e.get("DEF"): e for e in ROOT.iter("OrientationInterpolator")}
        for kind, insts, _ in T.AUTOMATA:
            times = sorted(t for i in insts for t in by.get(i, []))
            self.assertGreater(len(times), 20, kind)
            want = T.arm_events(kind, times)
            for side, arm in ((1, "R"), (-1, "L")):
                node = ints.get("Band_%s_arm%s_rot" % (kind, arm))
                if not want[side]:
                    self.assertIsNone(node, "%s arm %s has no events and must not be driven" % (kind, arm))
                    continue
                self.assertIsNotNone(node, (kind, arm))
                keys = [float(x) for x in node.get("key").split()]
                vals = node.get("keyValue").split()
                ang = [float(vals[i + 3]) for i in range(0, len(vals), 4)]
                hits = [k * CARD.D for k, a in zip(keys, ang) if abs(a - T.ARM_HIT) < 1e-6]
                self.assertEqual(len(hits), len(want[side]), (kind, arm))
                for h, t in zip(hits, want[side]):
                    self.assertAlmostEqual(h, t, delta=2e-3, msg=(kind, arm))
            self.assertEqual(sorted(want[1] + want[-1]), times if kind != "cymbal" else sorted(times + times))


if __name__ == "__main__":
    unittest.main()
