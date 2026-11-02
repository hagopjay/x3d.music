"""The Score witness must pass the real cards and go red on damaged ones: a witness that cannot fail proves nothing. Needs music21 (the score job installs it)."""
import copy, json, os, sys, unittest
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "score"))
try:
    import music21          # noqa: F401
except ImportError:
    music21 = None
if music21 is not None:
    import score_check as W
    import tracks as T

SKIP = "music21 is not installed (the CI score job installs requirements-score.txt)"


def load(piece):
    cp = os.path.join(ROOT, "score", piece + ".score.json")
    return json.load(open(cp, encoding="utf-8")), json.load(open(os.path.join(ROOT, "tracks", piece + ".tracks.json"), encoding="utf-8")), cp


def red(card, piece, tracks=None, cp=None):
    return {r["id"] for r in W.check_piece(card, piece, ROOT, tracks, cp) if not r["ok"]}


@unittest.skipIf(music21 is None, SKIP)
class Pristine(unittest.TestCase):
    def test_both_cards_and_their_tracks_pass(self):
        for piece in ("turca", "ode"):
            card, tracks, cp = load(piece)
            self.assertEqual(red(card, piece, tracks, cp), set(), piece)


@unittest.skipIf(music21 is None, SKIP)
class DamagedTurca(unittest.TestCase):
    def setUp(self):
        self.card, self.tracks, self.cp = load("turca")

    def notes(self):
        return self.card["notes"]

    def test_changed_pitch(self):
        self.notes()[40]["pitch"] += 1
        self.assertTrue({"S1", "S3b"} <= red(self.card, "turca"))

    def test_dropped_note(self):
        del self.notes()[100]
        self.assertTrue({"S1", "S6b"} <= red(self.card, "turca"))

    def test_extra_note(self):
        extra = copy.deepcopy(self.notes()[10])
        extra["id"] = "turca.A1.pno.R.9999"
        self.notes().append(extra)
        self.assertIn("S1", red(self.card, "turca"))

    def test_moved_onset(self):
        n = self.notes()[200]
        q = Fr(n["q"]) + Fr(1, 16)
        n["q"] = str(q.numerator) if q.denominator == 1 else "%d/%d" % (q.numerator, q.denominator)
        self.assertIn("S1", red(self.card, "turca"))

    def test_seconds_that_disagree_with_the_tempo_map(self):
        self.notes()[300]["t"] += 0.01
        self.assertIn("S4", red(self.card, "turca"))

    def test_grace_note_moved(self):
        g = next(n for n in self.notes() if n.get("g"))
        g["t"] -= 0.02
        self.assertIn("S4", red(self.card, "turca"))

    def test_duplicate_id(self):
        self.notes()[501]["id"] = self.notes()[500]["id"]
        self.assertIn("S6a", red(self.card, "turca"))

    def test_wrong_section_label(self):
        self.notes()[600]["section"] = "Z"
        self.assertTrue({"S1", "S6b"} <= red(self.card, "turca"))

    def test_source_changed_under_the_card(self):
        self.card["source"]["sha256"] = "0" * 64
        self.assertIn("S0", red(self.card, "turca"))

    def test_wrong_bar_count(self):
        self.card["checks"]["bars_performed"] = 223
        self.assertIn("S3c", red(self.card, "turca"))

    def test_a_pass_missing_from_the_form(self):
        del self.card["form"][3]
        self.assertIn("S2a", red(self.card, "turca"))

    def test_harmony_with_a_hole(self):
        del self.card["harmony"][50]
        self.assertIn("S7", red(self.card, "turca"))

    def test_harmony_tension_edited(self):
        self.card["harmony"][5]["tension"] += 0.5
        self.assertIn("S7", red(self.card, "turca"))

    def test_velocity_is_performance_not_source(self):
        for n in self.notes():
            n["vel"] = 100
        self.assertEqual(red(self.card, "turca"), set())

    def test_tracks_that_do_not_match_the_card(self):
        t = copy.deepcopy(self.tracks)
        raw = T.unpack(t["channels"]["tension"]["b64"], t["n"])
        t["channels"]["tension"]["b64"] = T.pack([v + 7 for v in raw])
        self.assertIn("T1", red(self.card, "turca", t, self.cp))

    def test_tracks_bound_to_another_card(self):
        t = copy.deepcopy(self.tracks)
        t["card_sha256"] = "1" * 64
        self.assertIn("T0", red(self.card, "turca", t, self.cp))


@unittest.skipIf(music21 is None, SKIP)
class DamagedOde(unittest.TestCase):
    def setUp(self):
        self.card, self.tracks, self.cp = load("ode")

    def test_the_tie_broken_into_two_notes(self):
        n = next(n for n in self.card["notes"] if n.get("tied"))
        n["ql"] = "1"
        self.assertTrue({"S1", "S3e"} <= red(self.card, "ode"))

    def test_a_melody_note_missing_from_the_coda(self):
        i = max(i for i, n in enumerate(self.card["notes"]) if n["section"] == "Coda" and n["layer"] == "composer")
        del self.card["notes"][i]
        self.assertIn("S1", red(self.card, "ode"))

    def test_the_form_is_not_the_spec_table(self):
        self.card["form"][3]["bars"] = [41, 56]
        self.assertIn("S2d", red(self.card, "ode"))

    def test_the_tempo_map_edited_without_the_seconds(self):
        self.card["tempo_map"][0]["qpm"] = 120
        self.assertTrue({"S4", "S2b"} & red(self.card, "ode"))


@unittest.skipIf(music21 is None, SKIP)
class DamagedArrangement(unittest.TestCase):
    """The arrangement layer is ours, so the witness checks it for what can be checked: provenance, instruments, timing, place in the form, and the Ode's routing and counter-line."""

    def arr(self, card, rule=None):
        return next(n for n in card["notes"] if n["layer"] == "arrangement" and (rule is None or n["src"] == "arr:" + rule))

    def test_a_note_without_its_rule(self):
        card, _, _ = load("turca")
        del self.arr(card)["src"]
        self.assertIn("S11", red(card, "turca"))

    def test_an_arrangement_note_that_pretends_to_have_a_kern_bar(self):
        card, _, _ = load("turca")
        self.arr(card)["kbar"] = 3
        self.assertIn("S11", red(card, "turca"))

    def test_the_card_miscounts_its_arrangement(self):
        card, _, _ = load("ode")
        card["checks"]["arrangement_notes"] -= 1
        self.assertIn("S11", red(card, "ode"))

    def test_an_arrangement_note_on_the_composers_instrument(self):
        card, _, _ = load("turca")
        self.arr(card)["inst"] = "pno"
        self.assertIn("S12", red(card, "turca"))

    def test_an_undeclared_instrument(self):
        card, _, _ = load("turca")
        card["instruments"] = [i for i in card["instruments"] if i["id"] != "brass"]
        self.assertIn("S13", red(card, "turca"))

    def test_a_stem_with_the_wrong_name(self):
        card, _, _ = load("turca")
        next(i for i in card["instruments"] if i["id"] == "bass")["stem"] = "stems/bass_new.wav"
        self.assertIn("S13", red(card, "turca"))

    def test_an_arrangement_note_that_drifted_from_the_tempo_map(self):
        card, _, _ = load("turca")
        self.arr(card)["t"] += 0.004
        self.assertIn("S14", red(card, "turca"))

    def test_an_arrangement_note_in_the_wrong_pass(self):
        card, _, _ = load("turca")
        self.arr(card)["rep"] = 2
        self.assertIn("S14", red(card, "turca"))

    def test_an_arrangement_note_ringing_past_the_end(self):
        card, _, _ = load("ode")
        n = [n for n in card["notes"] if n["layer"] == "arrangement"][-1]
        n["ql"] = "50"
        self.assertIn("S14", red(card, "ode"))

    def test_a_velocity_out_of_range(self):
        card, _, _ = load("turca")
        self.arr(card)["vel"] = 200
        self.assertIn("S15", red(card, "turca"))

    def test_a_composer_instrument_left_without_a_stem(self):
        card, _, _ = load("turca")
        card["instruments"] = [i for i in card["instruments"] if i["id"] != "pno"]
        self.assertTrue({"S10", "S16"} <= red(card, "turca"))

    def test_a_section_with_no_route(self):
        card, _, _ = load("ode")
        del card["routing"]["mel"]["S3"]
        self.assertIn("S16", red(card, "ode"))

    def test_a_route_to_an_undeclared_instrument(self):
        card, _, _ = load("ode")
        card["routing"]["mel"]["S2"][0]["inst"] = "theremin"
        self.assertTrue({"S13", "S16"} <= red(card, "ode"))

    def test_a_route_that_shifts_ten_octaves(self):
        card, _, _ = load("ode")
        card["routing"]["mel"]["S1"][0]["rel"] = 10
        self.assertIn("S16", red(card, "ode"))

    def test_a_counter_line_note_a_fourth_from_the_melody(self):
        card, _, _ = load("ode")
        self.arr(card, "counter.line")["pitch"] += 2                     # the first note sounds a minor tenth over the melody; two semitones more is a fourth over it
        self.assertIn("S17", red(card, "ode"))

    def test_a_counter_line_note_under_the_melody(self):
        card, _, _ = load("ode")
        self.arr(card, "counter.line")["pitch"] -= 24
        self.assertIn("S17", red(card, "ode"))


if __name__ == "__main__":
    unittest.main()
