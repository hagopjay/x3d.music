"""The Turca's chord labeller: the bass is a left-hand note, a beat without one is not a chord change, an oom-pah bar is one chord, and equal chords merge whatever the bass."""
import os, sys, unittest
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harmony as H       # noqa: E402

A, C, E, G_SHARP, B, D = 9, 0, 4, 8, 11, 2        # pitch classes
A3, C4, E4, B4, GS4, A4, E3, B3, GS3 = 57, 60, 64, 71, 68, 69, 52, 59, 56


def label(spans, q0, q1, key, prev=None):
    return [(str(a), str(b), H.NAMES[r] + qual, H.NAMES[bs]) for a, b, r, qual, bs in H.label_section(spans, Fr(q0), Fr(q1), key, prev=prev)]


class Labeller(unittest.TestCase):
    def test_right_hand_alone_takes_the_tonic(self):
        # the Turca's opening upbeat: B A G# A in sixteenths, left hand resting, nothing before it
        spans = [(Fr(0), Fr(1, 4), B4, False), (Fr(1, 4), Fr(1, 2), A4, False), (Fr(1, 2), Fr(3, 4), GS4, False), (Fr(3, 4), Fr(1), A4, False)]
        self.assertEqual(label(spans, 0, 1, "a"), [("0", "1", "Am", "A")])
        self.assertEqual(label(spans, 0, 1, "A"), [("0", "1", "AM", "A")])

    def test_a_rest_keeps_the_chord_before(self):
        # bar of A minor (bass A3 with C4+E4 above it), then a beat where only the right hand sounds
        spans = [(Fr(0), Fr(1), A3, True), (Fr(0), Fr(1), C4, True), (Fr(0), Fr(1), E4, True), (Fr(1), Fr(2), B4, False), (Fr(1), Fr(2), GS4, False)]
        self.assertEqual(label(spans, 0, 2, "a"), [("0", "2", "Am", "A")])

    def test_a_rest_never_takes_a_chord_of_the_old_key(self):
        # the chord before this stretch is G major (the old key's dominant); a left-hand rest in the new key starts on its own tonic
        spans = [(Fr(0), Fr(1), B4, False)]
        prev = (7, "M", 7)
        self.assertEqual(label(spans, 0, 1, "a", prev=prev), [("0", "1", "Am", "A")])

    def test_oom_pah_bar_is_one_chord(self):
        # A3 on the beat, C4+E4 on the off-beat and again on the next beat: the dyad's low C is not a bass
        spans, t = [], Fr(0)
        for bar in range(3):
            spans += [(t, t + Fr(1, 2), A3, True), (t + Fr(1, 2), t + 1, C4, True), (t + Fr(1, 2), t + 1, E4, True),
                      (t + 1, t + Fr(3, 2), C4, True), (t + 1, t + Fr(3, 2), E4, True), (t + Fr(3, 2), t + 2, C4, True), (t + Fr(3, 2), t + 2, E4, True)]
            spans += [(t, t + 1, A4, False), (t + 1, t + 2, 72, False)]        # melody on A then C
            t += 2
        self.assertEqual(label(spans, 0, 6, "a"), [("0", "6", "Am", "A")])

    def test_a_real_change_of_bass_is_a_new_chord(self):
        spans = [(Fr(0), Fr(2), A3, True), (Fr(0), Fr(2), C4, True), (Fr(0), Fr(2), E4, True),
                 (Fr(2), Fr(4), E3, True), (Fr(2), Fr(4), GS3, True), (Fr(2), Fr(4), B3, True), (Fr(2), Fr(4), GS4, False)]
        got = label(spans, 0, 4, "a")
        self.assertEqual([(a, b, c) for a, b, c, _ in got], [("0", "2", "Am"), ("2", "4", "EM")])

    def test_equal_chords_merge_whatever_the_bass(self):
        # A minor over A, then A minor over C (first inversion), then over E: one segment, and the figure is read from the bass where it began
        spans = []
        for i, bass in enumerate((A3, C4, E4)):
            spans += [(Fr(i), Fr(i + 1), bass, True), (Fr(i), Fr(i + 1), A4, False), (Fr(i), Fr(i + 1), 72, False), (Fr(i), Fr(i + 1), 76, False)]
        got = H.label_section(spans, Fr(0), Fr(3), "a")
        self.assertEqual(len(got), 1)
        self.assertEqual(H.roman(got[0][2], got[0][3], got[0][4], "a"), "i")

    def test_the_right_hand_is_never_the_bass(self):
        # a right-hand note below the left hand's lowest note does not become the bass
        spans = [(Fr(0), Fr(1), E4, True), (Fr(0), Fr(1), 55, False), (Fr(0), Fr(1), C4, True)]
        (q0, q1, root, qual, bass), = H.label_section(spans, Fr(0), Fr(1), "C")
        self.assertEqual(bass, C)


if __name__ == "__main__":
    unittest.main()
