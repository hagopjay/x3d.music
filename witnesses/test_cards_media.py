"""Tests for the page's cards: the media tool leaves nothing in a card but pixels and our own comment, and the page builder ships a card only when its files match the manifest.
Needs ffmpeg and ffprobe (the sweep job has none, so these skip there; the page job installs them and runs the same checks through the Cards test)."""
import json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for sub in ("tools", "witnesses", "page", "gen"):
    sys.path.insert(0, os.path.join(ROOT, sub))

HAVE = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
if HAVE:
    import prep_cards as PC           # noqa: E402
    import leak_sweep as LS           # noqa: E402

TAGS_OK = {"language", "handler_name", "vendor_id", "major_brand", "minor_version", "compatible_brands", "comment"}


@unittest.skipUnless(HAVE, "ffmpeg is not installed")
class Cards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        PC.main(["--synthetic", "--out", cls.tmp])
        with open(os.path.join(cls.tmp, "cards.json"), encoding="utf-8") as f:
            cls.man = json.load(f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_four_cards_with_posters_and_the_manifest_says_what_they_are(self):
        self.assertTrue(self.man["synthetic"])
        self.assertEqual(sorted(self.man["cards"]), ["between", "ode", "title", "turca"])
        for cid, c in self.man["cards"].items():
            for k in ("video", "poster"):
                self.assertTrue(os.path.isfile(os.path.join(self.tmp, c[k])), (cid, k))
            self.assertEqual(c["sha256"], PC.sha_file(os.path.join(self.tmp, c["video"])))
            self.assertEqual(c["poster_sha256"], PC.sha_file(os.path.join(self.tmp, c["poster"])))
            self.assertTrue(c["label"].startswith("Test pattern"), cid)             # a test pattern never calls itself AI-made
            self.assertGreater(c["seconds"], 1.5)

    def test_nothing_in_a_video_but_our_comment(self):
        for cid, c in self.man["cards"].items():
            p = os.path.join(self.tmp, c["video"])
            data = open(p, "rb").read()
            for needle in (b"x264", b"Lavc", b"Lavf", b"libx264"):
                self.assertNotIn(needle, data, (cid, needle))
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", p], capture_output=True, text=True, check=True).stdout
            j = json.loads(out)
            tags = dict(j.get("format", {}).get("tags", {}))
            for st in j.get("streams", []):
                tags.update(st.get("tags", {}))
            self.assertTrue(set(tags) <= TAGS_OK, (cid, sorted(set(tags) - TAGS_OK)))
            self.assertTrue(tags["comment"].startswith("Test pattern"), cid)

    def test_no_sound_and_one_video_stream(self):
        for cid, c in self.man["cards"].items():
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name", "-of", "json", os.path.join(self.tmp, c["video"])], capture_output=True, text=True, check=True).stdout
            streams = json.loads(out)["streams"]
            self.assertEqual([(s["codec_type"], s["codec_name"]) for s in streams], [("video", "h264")], cid)

    def test_posters_pass_the_sweeps_image_rule(self):
        for cid, c in self.man["cards"].items():
            self.assertEqual(LS.scan_image(c["poster"], open(os.path.join(self.tmp, c["poster"]), "rb").read()), [], cid)

    def test_the_page_builder_ships_only_cards_that_match(self):
        import build_page as BP
        with tempfile.TemporaryDirectory() as out:
            shipped, synthetic = BP.cards_from(self.tmp, out)
            self.assertTrue(synthetic)
            self.assertEqual(sorted(shipped), ["between", "ode", "title", "turca"])
            self.assertTrue(all(os.path.isfile(os.path.join(out, v["video"])) and os.path.isfile(os.path.join(out, v["poster"])) for v in shipped.values()))
        bad = tempfile.mkdtemp()
        try:
            shutil.copytree(self.tmp, bad, dirs_exist_ok=True)
            with open(os.path.join(bad, "ode.jpg"), "ab") as f:                      # one byte more than the manifest knows
                f.write(b"x")
            os.remove(os.path.join(bad, "turca.mp4"))                                 # and a missing file
            with tempfile.TemporaryDirectory() as out:
                shipped, _ = BP.cards_from(bad, out)
                self.assertEqual(sorted(shipped), ["between", "title"])
                self.assertFalse(os.path.exists(os.path.join(out, "cards", "ode.mp4")))
        finally:
            shutil.rmtree(bad, ignore_errors=True)
        with tempfile.TemporaryDirectory() as empty, tempfile.TemporaryDirectory() as out:
            self.assertEqual(BP.cards_from(empty, out), ({}, False))                  # no media folder, no cards


if __name__ == "__main__":
    unittest.main()
