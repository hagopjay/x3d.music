"""Tests for the Ode's picture: the AI-made image woven through the five threads, the stand-in it falls back to, and the art switch (gen/artlib.py)."""
import io, json, os, sys, tempfile, unittest

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artlib                    # noqa: E402
import picture_ode as PIC        # noqa: E402

LIN = lambda rgb: (np.array(rgb, float) / 255.0) ** 2.2


def flat(rgb, n=48):
    return np.full((n, n, 3), rgb, np.uint8)


def cell_at(cb, r, c):
    return int(cb[r, c] & 7), int(cb[r, c] >> 3)


class Quantize(unittest.TestCase):
    def test_each_thread_is_found_from_its_own_colour(self):
        for k, ink in enumerate(PIC.INK[:4], start=1):
            cb = PIC.quantize(np.tile(flat(ink)[:1], (384, 256, 1)))
            self.assertEqual(set(np.unique(cb & 7)), {k}, PIC.NAMES[k])
            tone = int(np.median(cb >> 3))
            s = PIC.LO + (PIC.HI - PIC.LO) * tone / 31.0
            self.assertAlmostEqual(s, 1.0, delta=0.06, msg=PIC.NAMES[k])                       # the ink as painted is brightness 1

    def test_dark_pixels_are_the_darkest_indigo_and_light_greys_are_silver(self):
        cb = PIC.quantize(np.tile(flat((10, 10, 30))[:1], (384, 256, 1)))
        self.assertEqual(set(np.unique(cb & 7)), {1})
        self.assertEqual(int(np.median(cb >> 3)), 0)                                         # held to the weave's darkest
        cb = PIC.quantize(np.tile(flat((170, 176, 192))[:1], (384, 256, 1)))
        self.assertEqual(set(np.unique(cb & 7)), {2})

    def test_cream_is_ivory_and_sand_is_gold(self):
        self.assertEqual(set(np.unique(PIC.quantize(np.tile(flat((236, 228, 200))[:1], (384, 256, 1))) & 7)), {4})
        self.assertEqual(set(np.unique(PIC.quantize(np.tile(flat((196, 156, 72))[:1], (384, 256, 1))) & 7)), {3})

    def test_any_size_in_the_cell_grid_out_and_crimson_is_never_chosen(self):
        rng = np.random.RandomState(7)
        cb = PIC.quantize(rng.randint(0, 256, (300, 200, 3)).astype(np.uint8))
        self.assertEqual(cb.shape, (PIC.CH, PIC.CW))
        self.assertEqual(cb.dtype, np.uint8)
        self.assertTrue(set(np.unique(cb & 7)) <= {1, 2, 3, 4})


class Source(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.tmp.name
        rng = np.random.RandomState(3)
        # a small three-by-four picture of blocks in four inks, 3:4 like the real one
        im = np.zeros((768, 512, 3), np.uint8)
        for r in range(4):
            for c in range(3):
                im[r * 192:(r + 1) * 192, c * 171:(c + 1) * 171] = PIC.INK[(r + c) % 4]
        im = np.clip(im.astype(int) + rng.randint(-6, 7, im.shape), 0, 255).astype(np.uint8)
        Image.fromarray(im).save(os.path.join(d, "ode-tapestry.png"))
        data = open(os.path.join(d, "ode-tapestry.png"), "rb").read()
        json.dump({"items": {"ode-tapestry": {"file": "ode-tapestry.png", "use": "ai", "sha256": artlib.sha256_file(os.path.join(d, "ode-tapestry.png"))}}}, open(os.path.join(d, "manifest.json"), "w"))
        cls.dir = d

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.keep = {k: os.environ.pop(k, None) for k in ("LOOM_ART", "LOOM_ART_ODE_TAPESTRY", "LOOM_ART_DIR")}
        self.old = artlib.ART
        artlib.ART = self.dir

    def tearDown(self):
        artlib.ART = self.old
        for k, v in self.keep.items():
            if v is not None:
                os.environ[k] = v

    def test_the_picture_is_woven_with_two_crimson_border_threads_and_nothing_else_crimson(self):
        cb = PIC.cells()
        cls = cb & 7
        self.assertEqual(cb.shape, (384, 256))
        self.assertEqual(int((cls == PIC.CRIMSON).sum()), 2 * 384)
        self.assertTrue(set(np.unique(cls)) <= set(range(1, 6)))
        self.assertTrue((cls[:, 7] == PIC.CRIMSON).all() and (cls[:, 248] == PIC.CRIMSON).all())
        self.assertEqual(int(np.count_nonzero(cls == 0)), 0)                                  # no bare linen inside the picture

    def test_blocks_come_out_as_their_threads(self):
        cb = PIC.cells()
        cls = cb & 7
        # block (r, c) was ink (r + c) % 4; look at its middle, away from the crimson border threads and the resampling edges
        for r in range(4):
            for c in range(3):
                y, x = int((r + 0.5) * 96), int((c + 0.5) * 85.3)
                self.assertEqual(int(cls[y, x]), (r + c) % 4 + 1, (r, c))

    def test_deterministic(self):
        self.assertTrue(np.array_equal(PIC.cells(), PIC.cells()))

    def test_the_stand_in_is_still_there_when_asked_for_and_is_the_original_picture(self):
        os.environ["LOOM_ART"] = "procedural"
        try:
            cb = PIC.cells()
        finally:
            del os.environ["LOOM_ART"]
        self.assertTrue(np.array_equal(cb, PIC.cells_procedural()))
        for k in range(1, 6):
            self.assertGreater(int(((cb & 7) == k).sum()), 300, PIC.NAMES[k])

    def test_a_changed_or_missing_file_never_gets_used(self):
        with tempfile.TemporaryDirectory() as d:
            man = json.load(open(os.path.join(self.dir, "manifest.json")))
            data = open(os.path.join(self.dir, "ode-tapestry.png"), "rb").read()
            open(os.path.join(d, "ode-tapestry.png"), "wb").write(data + b"x")                  # one byte more than the manifest knows
            json.dump(man, open(os.path.join(d, "manifest.json"), "w"))
            use, why = artlib.status("ode-tapestry", d)
            self.assertEqual(use, "procedural")
            self.assertIn("sha256", why)
            os.remove(os.path.join(d, "ode-tapestry.png"))
            use, why = artlib.status("ode-tapestry", d)
            self.assertEqual((use, why.split(":")[0]), ("procedural", "file missing"))
        self.assertEqual(artlib.status("no-such-item", self.dir)[0], "procedural")

    def test_environment_overrides_the_manifest(self):
        os.environ["LOOM_ART_ODE_TAPESTRY"] = "procedural"
        try:
            self.assertEqual(artlib.use("ode-tapestry"), "procedural")
        finally:
            del os.environ["LOOM_ART_ODE_TAPESTRY"]
        self.assertEqual(artlib.use("ode-tapestry"), "ai")

    def test_accents(self):
        self.assertEqual(int(PIC.accents(False).sum()), 2 * PIC.CH)
        self.assertGreater(int(PIC.accents(True).sum()), 2 * PIC.CH + 500)


class CommittedArt(unittest.TestCase):
    """Whatever art/ holds is what its manifest says, and carries nothing but pixels and our own label."""

    def test_every_item_matches_its_manifest(self):
        art = os.path.join(artlib.ROOT, "art")
        man = artlib.manifest(art)
        for name, it in man.get("items", {}).items():
            p = os.path.join(art, it["file"])
            self.assertTrue(os.path.isfile(p), name)
            self.assertEqual(artlib.sha256_file(p), it["sha256"], name)
            self.assertLess(os.path.getsize(p), 5 * 1024 * 1024, name)                           # the repository's cap for media


if __name__ == "__main__":
    unittest.main()
