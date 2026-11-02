"""Exact fractions, the tempo map, bar and beat, velocity from dynamics, and deterministic packing of tracks."""
import os, sys, unittest
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cardlib as C       # noqa: E402
import harmony as H       # noqa: E402
import tracks as T        # noqa: E402


class Fractions(unittest.TestCase):
    def test_round_trip(self):
        for x in (Fr(0), Fr(3), Fr(1, 4), Fr(437, 2), Fr(-5, 8)):
            self.assertEqual(C.unfrac(C.frac(x)), x)
        self.assertEqual(C.frac(Fr(6, 2)), "3")


class Tempo(unittest.TestCase):
    def test_constant(self):
        tm = C.TempoMap([(0, 120)])
        self.assertEqual(tm.seconds(4), Fr(2))
        self.assertEqual(tm.quarters(Fr(1, 2)), Fr(1))

    def test_steps_are_exact_and_invertible(self):
        tm = C.TempoMap([(0, 120), (4, 60), (8, 30)])
        self.assertEqual(tm.seconds(4), Fr(2))
        self.assertEqual(tm.seconds(8), Fr(6))
        self.assertEqual(tm.seconds(10), Fr(10))
        for q in (Fr(0), Fr(1, 3), Fr(4), Fr(23, 5), Fr(9)):
            self.assertEqual(tm.quarters(tm.seconds(q)), q)
        self.assertEqual(tm.spq(5), Fr(1))


class Metric(unittest.TestCase):
    def test_upbeat_piece(self):
        self.assertEqual(C.metric(0, 1, 2), (0, 2))              # the pickup: bar 0, beat 2
        self.assertEqual(C.metric(Fr(1, 4), 1, 2), (0, Fr(9, 4)))
        self.assertEqual(C.metric(1, 1, 2), (1, 1))
        self.assertEqual(C.metric(16, 1, 2), (8, 2))             # the next pass's upbeat closes bar 8

    def test_no_upbeat(self):
        self.assertEqual(C.metric(0, 0, 4), (1, 1))
        self.assertEqual(C.metric(Fr(9, 2), 0, 4), (2, Fr(3, 2)))


class Velocity(unittest.TestCase):
    def test_levels_accent_and_ramp(self):
        v = C.velocity_fn([(Fr(0), "p"), (Fr(10), "<"), (Fr(12), "sfp"), (Fr(20), "f")])
        self.assertEqual(v(Fr(0)), 50)
        self.assertEqual(v(Fr(9)), 50)
        self.assertEqual(v(Fr(11)), 82)                          # half way from 50 to the sf level 114
        self.assertEqual(v(Fr(12)), 114)
        self.assertEqual(v(Fr(13)), 50)
        self.assertEqual(v(Fr(20)), 96)


class Packing(unittest.TestCase):
    def test_pack_is_reproducible_and_round_trips(self):
        a = [0, 1, 999, -3, 12, 12, 12]
        s = T.pack(a)
        self.assertEqual(s, T.pack(a))
        self.assertEqual(T.unpack(s, len(a)), a)

    def test_page_part_decodes_with_gzip(self):
        import base64, gzip, struct
        a = [3, 1, 4, 1, 5, 9, 2, 6] * 50
        raw = gzip.decompress(base64.b64decode(T.page_part(a)))
        self.assertEqual(list(struct.unpack("<%dh" % len(a), raw)), a)


class Spiral(unittest.TestCase):
    def test_line_of_fifths_window(self):
        self.assertEqual(H.fifths_index(1, 3), 7)                # C sharp in A major sits at 7, not -5
        self.assertEqual(H.fifths_index(8, 3), 8)
        self.assertEqual(H.tonic_index(9), 3)
        self.assertEqual(H.tonic_index(6), 6)

    def test_tonic_is_calmer_than_dominant(self):
        self.assertLess(H.tension(9, "m", "a"), H.tension(4, "M", "a"))
        self.assertLess(H.tension(2, "M", "D"), H.tension(9, "M", "D"))

    def test_numerals(self):
        self.assertEqual(H.roman(9, "m", 9, "a"), "i")
        self.assertEqual(H.roman(4, "7", 4, "a"), "V7")
        self.assertEqual(H.roman(4, "7", 8, "a"), "V65")
        self.assertEqual(H.roman(2, "m", 5, "a"), "iv6")
        self.assertEqual(H.roman(9, "M", 9, "A"), "I")
        self.assertEqual(H.roman(0, "M", 4, "C"), "I6")


if __name__ == "__main__":
    unittest.main()
