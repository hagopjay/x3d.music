#!/usr/bin/env python3
"""The atlas probe: build/probes/probe_atlas.x3d (+ art/dome-motifs.jpg beside it).

A flat page of twelve cells, each showing one motif of the dome's atlas through the dome's own lookup (gen/shaders/motif_lib.glsl). witnesses/atlas_test.mjs photographs it and compares every cell
with the picture in art/dome-motifs.jpg, which is how the lookup's idea of which way is up gets checked against what X_ITE really does. Not a world: it has no score and no page.
"""
import os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import artlib                                                           # noqa: E402
import worldlib as W                                                    # noqa: E402
from x3dw import N, document, mf, route, shader, time_bus               # noqa: E402

OUT = os.path.join(HERE, "..", "..", "build", "probes")
D = 10.0


def build(out=None):
    out = out or OUT
    use, why = artlib.status("dome-motifs")
    if use != "ai":
        raise SystemExit("the atlas probe needs the dome's picture (art/dome-motifs.jpg): %s" % why)
    it = artlib.manifest()["items"]["dome-motifs"]
    os.makedirs(os.path.join(out, "art"), exist_ok=True)
    shutil.copyfile(artlib.path("dome-motifs"), os.path.join(out, "art", it["file"]))
    props = N("TextureProperties", containerField="textureProperties", generateMipMaps=True, minificationFilter="AVG_PIXEL_AVG_MIPMAP", magnificationFilter="AVG_PIXEL",
              boundaryModeS="CLAMP_TO_EDGE", boundaryModeT="CLAMP_TO_EDGE", anisotropicDegree=8)
    tex = N("ImageTexture", props, DEF="Pic_motifs", url='"art/%s"' % it["file"], repeatS=False, repeatT=False)
    sh = shader("ShAtlasProbe", [("u_time", "SFFloat", "inputOutput", 0), ("u_dur", "SFFloat", "inputOutput", D), ("u_idpass", "SFFloat", "inputOutput", 0), ("u_calm", "SFFloat", "inputOutput", 0),
                                 ("u_motifs", "SFNode", "inputOutput", tex)], W.stage("atlas_probe_vs"), W.stage("atlas_probe_fs"))
    quad = N("IndexedTriangleSet", N("Coordinate", point=mf([-2, -1.5, 0, 2, -1.5, 0, 2, 1.5, 0, -2, 1.5, 0])), index="0 1 2 0 2 3", solid=False)
    kids = [N("OrthoViewpoint", DEF="Cam", position="0 0 5", fieldOfView="-2 -1.5 2 1.5", description="atlas probe"), N("NavigationInfo", type='"NONE"', headlight=False),
            N("Background", skyColor="0 0 0")]
    kids += time_bus(D)
    kids += [N("Shape", N("Appearance", sh), quad), route("SecondsBus", "value_changed", "ShAtlasProbe", "u_time")]
    text = document(kids, components=[("Interpolation", 2), ("Navigation", 3), ("Shaders", 1), ("Texturing", 2), ("Geometry3D", 2)], title="Loomsong atlas probe",
                    description="The dome's motif lookup on a flat page", generator="loomsong gen/probes/make_atlas_probe.py")
    path = os.path.join(out, "probe_atlas.x3d")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


if __name__ == "__main__":
    print("wrote", build(sys.argv[1] if len(sys.argv) > 1 else None))
