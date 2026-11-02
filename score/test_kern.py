"""The kern reader: token cases, the strictness about unknown characters, and the counts on the real file."""
import os, sys, tempfile, unittest
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kern as K          # noqa: E402

KRN = os.path.join(HERE, "..", "sources", "sonata11-3.krn")


class Tokens(unittest.TestCase):
    def tok(self, s):
        return K.parse_token(s, "test")

    def test_duration_and_dots(self):
        self.assertEqual(self.tok("4c")["dur"], Fr(1))
        self.assertEqual(self.tok("8.ccc#L")["dur"], Fr(3, 4))
        self.assertEqual(self.tok("2ccc#:")["dur"], Fr(2))
        self.assertEqual(self.tok("16bLL")["dur"], Fr(1, 4))
        self.assertEqual(self.tok("4.a")["dur"], Fr(3, 2))

    def test_pitch_octaves_and_accidentals(self):
        self.assertEqual(self.tok("4c")["midi"], 60)
        self.assertEqual(self.tok("4cc")["midi"], 72)
        self.assertEqual(self.tok("4C")["midi"], 48)
        self.assertEqual(self.tok("4AA")["midi"], 45)
        self.assertEqual(self.tok("16g#")["midi"], 68)
        self.assertEqual(self.tok("4b-")["midi"], 70)
        self.assertEqual(self.tok("32ggnqLLL")["midi"], 79)          # an explicit natural changes nothing
        self.assertEqual(self.tok("4ccc#")["name"], "C#6")

    def test_marks(self):
        t = self.tok("(8A'L")
        self.assertTrue(t["stac"] and not t["grace"] and t["slur"] == "s")
        self.assertTrue(self.tok("32C#q")["grace"])
        self.assertTrue(self.tok("4cc#:")["arp"])
        self.assertTrue(self.tok("(8.btL")["trill"])
        self.assertTrue(self.tok("4ryy")["rest"])
        self.assertEqual(self.tok("8cc)")["slur"], "e")

    def test_unknown_characters_are_errors(self):
        for bad in ("4c_", "[4c", "4c]", "4c;", "4c^"):
            with self.assertRaises(K.KernError, msg=bad):
                self.tok(bad)


class Spines(unittest.TestCase):
    def parse(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".krn", delete=False, encoding="utf-8") as f:
            f.write(body)
        try:
            return K.parse(f.name)
        finally:
            os.unlink(f.name)

    def test_split_and_merge_keep_voices_apart(self):
        k = self.parse("**kern\t**kern\n*\t*^\n4c\t4e\t2g\n4d\t4f\t.\n*\t*v\t*v\n4e\t4a\n==\t==\n*-\t*-\n")
        # the right hand splits: a half note g in the second voice (R2) runs beside two quarters in the first; they merge at t = 2
        by = {(h.voice, h.midi): h for h in k.heads}
        self.assertEqual(by[("R2", 67)].dur, Fr(2))
        self.assertEqual(by[("L", 62)].t, Fr(1))
        self.assertEqual(by[("R", 65)].t, Fr(1))
        self.assertEqual(by[("R", 69)].t, Fr(2))

    def test_a_voice_that_stops_early_raises_at_the_merge(self):
        with self.assertRaises(K.KernError):
            self.parse("**kern\t**kern\n*\t*^\n4c\t4e\t2g\n4d\t.\t.\n*\t*v\t*v\n4e\t4a\n==\t==\n*-\t*-\n")     # the first voice has nothing for its second quarter

    def test_rows_that_disagree_in_time_raise(self):
        with self.assertRaises(K.KernError):
            self.parse("**kern\t**kern\n4c\t2e\n4d\t4f\n==\t==\n*-\t*-\n")           # right hand is still holding a half note when the left starts its second quarter


@unittest.skipUnless(os.path.exists(KRN), "the kern source is not in the tree")
class RealFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = K.parse(KRN)

    def test_counts(self):
        s = K.summary(self.k)
        self.assertEqual(s["heads"], 1613)
        self.assertEqual(s["by_voice"], {"R": 790, "L": 776, "R2": 47})
        self.assertEqual(s["graces"], 189)
        self.assertEqual(s["midi"], [38, 88])
        self.assertEqual(s["end_q"], "256")

    def test_plan_and_labels(self):
        self.assertEqual(",".join(self.k.plan), "A,A,B,B,C,C,D,D,E,E,F,F,G,G,H,H,I,I1,I,I2,J")
        self.assertEqual([l for l, _, _ in self.k.labels], list("ABCDEFGHI") + ["I1", "I2", "J"])

    def test_section_lengths(self):
        t = {l: t for l, _, t in self.k.labels}
        self.assertEqual(t["B"] - t["A"], 16)
        self.assertEqual(t["I1"] - t["I"], 15)
        self.assertEqual(t["J"] - t["I2"], 2)


if __name__ == "__main__":
    unittest.main()
