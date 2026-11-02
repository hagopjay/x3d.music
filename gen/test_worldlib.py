#!/usr/bin/env python3
"""Tests for the pieces both worlds share (worldlib.py): the scene clock agrees with the audio master's, the bar grid agrees with the notes, an event texture reads back the events that
went into it, and the shot list obeys the camera grammar (cuts on phrase downbeats, moves of whole bars, pace follows density)."""
import math, os, random, re, sys, unittest
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import worldlib as W            # noqa: E402

ROOT = os.path.dirname(HERE)
CARDS = {p: W.Card(p) for p in ("turca", "ode")}


class Clock(unittest.TestCase):
    def test_the_ring_out_tails_equal_the_audio_masters(self):
        with open(os.path.join(ROOT, "audio", "render.py"), encoding="utf-8") as f:
            src = f.read()
        m = re.search(r"^TAILS\s*=\s*(\{[^}]*\})", src, re.M)
        self.assertIsNotNone(m, "audio/render.py has no TAILS table")
        self.assertEqual(eval(m.group(1), {}), W.TAILS)

    def test_the_scene_lasts_as_long_as_the_master(self):
        for piece, c in CARDS.items():
            self.assertAlmostEqual(c.D, c.seconds + W.TAILS[piece], places=3, msg=piece)

    def test_quarters_and_seconds_round_trip_through_the_tempo_map(self):
        for piece, c in CARDS.items():
            for n in c.composer()[:400]:
                if n.get("g"):
                    continue                                           # a grace note is played before its beat: its q is the beat it decorates
                self.assertAlmostEqual(c.q_t(Fr(n["q"])), n["t"], delta=2e-6, msg=n["id"])
                self.assertAlmostEqual(c.t_q(n["t"]), float(Fr(n["q"])), delta=2e-4, msg=n["id"])


class BarGrid(unittest.TestCase):
    def test_every_note_sits_on_the_bar_and_beat_the_card_gives_it(self):
        for piece, c in CARDS.items():
            for n in c.notes:
                q = float(c.bar_q(n["bar"])) + float(n["beat"]) - 1.0
                self.assertAlmostEqual(q, float(Fr(n["q"])), delta=1e-3, msg="%s %s" % (piece, n["id"]))

    def test_downbeats_are_whole_bars_and_increase(self):
        for piece, c in CARDS.items():
            db = c.downbeats()
            self.assertEqual(db[0]["bar"], 1)
            for a, b in zip(db, db[1:]):
                self.assertEqual(b["bar"], a["bar"] + 1)
                self.assertEqual(b["q"] - a["q"], c.beats)
                self.assertGreater(b["t"], a["t"])
            self.assertLess(db[-1]["t"], c.seconds + 1e-6)

    def test_every_pass_starts_on_a_known_quarter_and_passes_tile_the_piece(self):
        for piece, c in CARDS.items():
            self.assertEqual(c.passes[0]["q0"], 0)
            for a, b in zip(c.passes, c.passes[1:]):
                self.assertEqual(a["q1"], b["q0"], (piece, a["id"], b["id"]))
                self.assertAlmostEqual(a["t1"], b["t0"], places=3)


class Tables(unittest.TestCase):
    def test_a_table_reads_back_the_events_that_went_in(self):
        rnd = random.Random(7)
        D = 218.857
        rows = []
        for r in range(40):
            ev = []
            for _ in range(rnd.randint(0, 9)):
                on = rnd.uniform(0, D - 4)
                ev.append((on, on + rnd.uniform(0.02, 3), rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 9000)))
            rows.append(ev)
        tab = W.EventTable("t", rows, D)
        tex = tab.texels()
        res = 0.6 * D / W.T24
        for r, ev in enumerate(rows):
            got = tab.decode(r, tex)
            want = sorted(ev, key=lambda e: (e[0], e[1], e[5]))
            self.assertEqual(len(got), len(want))
            for g, w in zip(got, want):
                self.assertAlmostEqual(g[0], w[0], delta=res)
                self.assertAlmostEqual(g[1], w[1], delta=res)
                self.assertEqual(g[2:], w[2:])

    def test_texel_alpha_is_always_opaque_and_the_stream_wraps_at_1024(self):
        tab = W.EventTable("t", [[(1.0, 2.0, 3, 4, 5, 6)], []], 100.0)
        tex = tab.texels()
        self.assertEqual(len(tex) % W.EventTable.WIDTH, 0)
        self.assertTrue(all(int(t, 16) & 255 == 255 for t in tex))

    def test_a_time_resolves_far_finer_than_a_video_frame(self):
        D = 230.0
        worst = max(abs(W.from24(W.b24(t, D), D) - t) for t in (random.Random(3).uniform(0, D) for _ in range(5000)))
        self.assertLess(worst, 1e-5)


class Shots(unittest.TestCase):
    def test_cuts_land_on_downbeats_and_cover_the_piece_without_gaps(self):
        for piece, c in CARDS.items():
            blocks = W.shot_blocks(c)
            downs = [d["t"] for d in c.downbeats()]
            self.assertEqual(blocks[0]["t0"], 0.0)
            self.assertAlmostEqual(blocks[-1]["t1"], c.D, places=3)
            for a, b in zip(blocks, blocks[1:]):
                self.assertEqual(a["t1"], b["t0"])
            for b in blocks[1:]:
                self.assertTrue(any(abs(b["t0"] - t) < 1e-6 for t in downs), "%s: a cut at %.3f is not on a downbeat" % (piece, b["t0"]))

    def test_a_shot_is_a_whole_number_of_bars_except_the_last(self):
        for piece, c in CARDS.items():
            blocks = W.shot_blocks(c)
            downs = [d["t"] for d in c.downbeats()]
            for b in blocks[:-1]:
                self.assertTrue(any(abs(b["t1"] - t) < 1e-6 for t in downs), (piece, b["t1"]))

    def test_pace_follows_density_dense_shots_hold_one_phrase_sparse_ones_two(self):
        """Camera grammar 3: a busy passage cuts every phrase (4 bars, 5 when a one-bar stub joins), a sparse one holds two phrases per shot."""
        for piece, c in CARDS.items():
            downs = [d["t"] for d in c.downbeats()]
            blocks = W.shot_blocks(c)
            for b in blocks[:-1]:                                     # the last shot also holds the ring-out
                bars = sum(1 for t in downs if b["t0"] - 1e-6 <= t < b["t1"] - 1e-6)
                rate = c.onsets_per_second(b["t0"], b["t1"])
                self.assertLessEqual(bars, 10, (piece, b["t0"]))
                if rate >= 6.0:
                    self.assertLessEqual(bars, 5, (piece, b["t0"], rate))

    def test_a_cut_is_two_keys_one_hundred_and_twentieth_of_a_second_apart(self):
        shots = [W.Shot("a", 0.0, 4.0, (0, 0, 5), (0, 0, 0)), W.Shot("b", 4.0, 9.0, (3, 1, 5), (0, 0, 0))]
        vp, ints, routes = W.camera_nodes(shots, 10.0)
        pos = ints[0]
        keys = [float(x) for x in pos.attrs["key"].split()]
        i = next(k for k in range(len(keys) - 1) if keys[k + 1] - keys[k] < 0.01)
        self.assertAlmostEqual((keys[i + 1] - keys[i]) * 10.0, W.CUT_EPS, places=4)
        self.assertTrue(all(b > a for a, b in zip(keys, keys[1:])))


if __name__ == "__main__":
    unittest.main()
