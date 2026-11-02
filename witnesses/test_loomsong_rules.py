"""One passing and one failing case for each of the five Loomsong trap rules, plus the probe worlds as whole-file fixtures."""
import os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "gen"))
import loomsong_rules as R            # noqa: E402


def doc(body, version="4.1", head=""):
    return "<?xml version='1.0' encoding='UTF-8'?>\n<X3D profile='Immersive' version='%s'>\n<head>%s</head>\n<Scene>\n%s\n</Scene>\n</X3D>\n" % (version, head, body)


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def rules(text):
    return sorted({f["rule"] for f in R.check(text)})


SHADER_OK = ("<ScalarInterpolator DEF='SecondsBus' key='0 1' keyValue='0 10'/>"
             "<ComposedShader DEF='Sh' language='GLSL'><field name='u_time' type='SFFloat' accessType='inputOutput' value='0'/></ComposedShader>"
             "<ROUTE fromNode='SecondsBus' fromField='value_changed' toNode='Sh' toField='u_time'/>")
NEAREST = "<TextureProperties containerField='textureProperties' generateMipMaps='false' magnificationFilter='NEAREST_PIXEL' minificationFilter='NEAREST_PIXEL'/>"


def shader_with_texture(props):
    return ("<ScalarInterpolator DEF='SecondsBus' key='0 1' keyValue='0 10'/>"
            "<ComposedShader DEF='Sh' language='GLSL'><field name='u_time' type='SFFloat' accessType='inputOutput' value='0'/>"
            "<field name='u_events' type='SFNode' accessType='inputOutput'><PixelTexture image='1 1 4 0x000000FF'>%s</PixelTexture></field></ComposedShader>"
            "<ROUTE fromNode='SecondsBus' fromField='value_changed' toNode='Sh' toField='u_time'/>" % props)


class Rules(unittest.TestCase):
    def test_bus_wired_pass_and_fail(self):
        self.assertEqual(rules(doc(SHADER_OK)), [])
        no_route = SHADER_OK.replace("<ROUTE fromNode='SecondsBus' fromField='value_changed' toNode='Sh' toField='u_time'/>", "")
        self.assertEqual(rules(doc(no_route)), ["bus-wired"])
        no_field = SHADER_OK.replace("<field name='u_time' type='SFFloat' accessType='inputOutput' value='0'/>", "")
        self.assertIn("bus-wired", rules(doc(no_field)))
        wrong_bus = SHADER_OK.replace("fromNode='SecondsBus'", "fromNode='OtherBus'")
        self.assertEqual(rules(doc(wrong_bus)), ["bus-wired"])
        no_def = SHADER_OK.replace("<ComposedShader DEF='Sh'", "<ComposedShader")
        self.assertEqual(rules(doc(no_def)), ["bus-wired"])
        use_only = SHADER_OK + "<Shape><Appearance><ComposedShader USE='Sh'/></Appearance></Shape>"
        self.assertEqual(rules(doc(use_only)), [])                      # a USE is not a second definition

    def test_data_texture_nearest_pass_and_fail(self):
        self.assertEqual(rules(doc(shader_with_texture(NEAREST))), [])
        self.assertEqual(rules(doc(shader_with_texture(""))), ["data-texture-nearest"])
        linear = NEAREST.replace("minificationFilter='NEAREST_PIXEL'", "minificationFilter='AVG_PIXEL'")
        self.assertEqual(rules(doc(shader_with_texture(linear))), ["data-texture-nearest"])
        mips = NEAREST.replace("generateMipMaps='false'", "generateMipMaps='true'")
        self.assertEqual(rules(doc(shader_with_texture(mips))), ["data-texture-nearest"])
        unset = NEAREST.replace(" generateMipMaps='false'", "")
        self.assertEqual(rules(doc(shader_with_texture(unset))), ["data-texture-nearest"])

    def test_data_texture_rule_ignores_pictures(self):
        pic = ("<Shape><Appearance><ImageTexture url='\"a.png\"'/></Appearance></Shape>")
        self.assertEqual(rules(doc(pic)), [])                           # a texture in the Appearance slot is a picture, not data

    def test_splat_bbox_pass_and_fail(self):
        ok = "<GaussianSplats DEF='G' positions='0 0 0' bboxSize='1 1 1' bboxCenter='0 0 0'/>"
        self.assertEqual(rules(doc(ok)), [])
        self.assertEqual(rules(doc("<GaussianSplats DEF='G' positions='0 0 0' bboxCenter='0 0 0'/>")), ["splat-bbox"])
        self.assertEqual(rules(doc("<GaussianSplats DEF='G' positions='0 0 0'/>")), ["splat-bbox"])
        self.assertEqual(rules(doc(ok + "<GaussianSplats USE='G'/>")), [])

    def test_movie_not_still_pass_and_fail(self):
        self.assertEqual(rules(doc("<Shape><Appearance><MovieTexture url='\"a.mp4\" \"a.webm\"'/></Appearance></Shape>")), [])
        self.assertEqual(rules(doc("<Shape><Appearance><MovieTexture url='\"a.PNG\"'/></Appearance></Shape>")), ["movie-not-still"])
        self.assertEqual(rules(doc("<Shape><Appearance><MovieTexture url='\"a.mp4\" \"b.jpg?x=1\"'/></Appearance></Shape>")), ["movie-not-still"])

    def test_version_fits_nodes_pass_and_fail(self):
        g = "<GaussianSplats positions='0 0 0' bboxSize='1 1 1' bboxCenter='0 0 0'/>"
        self.assertEqual(rules(doc(g, version="4.1")), [])
        self.assertEqual(rules(doc(g, version="4.0")), ["version-fits-nodes"])
        self.assertEqual(rules(doc("<Group/>", version="4.0")), [])      # nothing 4.1-only: a 4.0 file is fine

    def test_finding_carries_a_line_number(self):
        f = R.check(doc("<GaussianSplats DEF='G' positions='0 0 0'/>"))[0]
        self.assertEqual((f["rule"], f["line"]), ("splat-bbox", 5))

    def test_probe_worlds(self):
        d = os.path.join(HERE, "..", "build", "probes")
        if not os.path.isdir(d):
            self.skipTest("run gen/probes/make_probes.py first")
        self.assertEqual(R.check(read(os.path.join(d, "probe_a.x3d"))), [])
        self.assertEqual(R.check(read(os.path.join(d, "probe_splat41.x3d"))), [])
        self.assertEqual(rules(read(os.path.join(d, "probe_splat40_bad.x3d"))), ["version-fits-nodes"])


if __name__ == "__main__":
    unittest.main()
