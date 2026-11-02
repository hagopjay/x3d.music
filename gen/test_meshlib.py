"""Invariants of the mesh library: every triangle's winding agrees with its stored normals, merging keeps indices and attributes consistent, transforms and the camera rotation do what they say."""
import math, os, sys, unittest
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import meshlib as M  # noqa: E402


def winding_agrees(mesh, min_dot=0.2):
    """Fraction of triangles whose geometric normal (from the index order) points the way the average stored vertex normal does."""
    P, F, Nn = mesh.P, mesh.F, mesh.N
    g = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    ln = np.linalg.norm(g, axis=1)
    ok = ln > 1e-12                                                     # degenerate triangles (poles) carry no direction
    g = g[ok] / ln[ok, None]
    s = Nn[F[ok]].mean(axis=1)
    s = s / np.maximum(np.linalg.norm(s, axis=1, keepdims=True), 1e-12)
    return float(np.mean(np.sum(g * s, axis=1) > min_dot))


class Primitives(unittest.TestCase):
    def test_every_primitive_faces_the_way_its_normals_say(self):
        shapes = {"box": M.box(1, 2, 3), "cylinder": M.cylinder(0.5, 0.3, 2, 12), "cone": M.cylinder(0.5, 0.0, 1, 12), "sphere": M.sphere(1, 16, 8), "torus": M.torus(1, 0.2, 16, 8),
                  "disc up": M.disc(1, 12, True), "disc down": M.disc(1, 12, False), "sector up": M.ring_sector(1, 2, 0.1, 0.7, 4, 0.0, True), "sector down": M.ring_sector(1, 2, 0.1, 0.7, 4, 0.0, False),
                  "arch": M.arch_prism(1.0, 2.0, 0.4, 8, 0.3), "extrusion": M.extrude_polygon([(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)], 0.5)}
        for name, m in shapes.items():
            with self.subTest(name):
                self.assertGreater(len(m.F), 0)
                self.assertEqual(winding_agrees(m), 1.0, name)

    def test_indices_stay_inside_the_vertex_arrays(self):
        for m in (M.box(), M.sphere(1, 8, 4), M.torus(1, 0.3, 8, 6), M.arch_prism(1, 2, 0.3, 6, 0.2)):
            self.assertLess(int(m.F.max()), len(m.P))
            self.assertEqual(len(m.P), len(m.N))
            self.assertEqual(len(m.P), len(m.C))

    def test_a_cylinder_has_the_right_size(self):
        c = M.cylinder(0.5, 0.5, 2.0, 16)
        self.assertAlmostEqual(float(c.P[:, 1].min()), 0.0)
        self.assertAlmostEqual(float(c.P[:, 1].max()), 2.0)
        self.assertAlmostEqual(float(np.hypot(c.P[:, 0], c.P[:, 2]).max()), 0.5, places=6)

    def test_the_arch_opening_is_where_it_says(self):
        a = M.arch_prism(1.0, 2.0, 0.4, 12, 0.3)
        self.assertAlmostEqual(float(a.P[:, 0].min()), -0.8)
        self.assertAlmostEqual(float(a.P[:, 0].max()), 0.8)
        self.assertAlmostEqual(float(a.P[:, 1].max()), 2.3)
        self.assertAlmostEqual(float(a.P[:, 2].min()), -0.2)
        inside = [p for p in a.P if abs(p[0]) < 0.45 and 0.1 < p[1] < 1.0]            # nothing solid in the opening's lower part
        self.assertEqual(inside, [])

    def test_ear_clipping_covers_a_concave_outline_exactly(self):
        pts = [(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)]                       # an L, area 3
        area = 0.0
        for i, j, k in M._ear_clip(pts):
            a, b, c = pts[i], pts[j], pts[k]
            area += 0.5 * abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
        self.assertAlmostEqual(area, 3.0)


class Merging(unittest.TestCase):
    def test_merge_offsets_indices_and_fills_missing_attributes(self):
        a = M.box().with_attr("id", [1.0])
        b = M.box()
        m = M.merge([a, b])
        self.assertEqual(len(m), len(a) + len(b))
        self.assertEqual(m.attrs["id"].shape, (len(m), 1))
        self.assertEqual(float(m.attrs["id"][len(a):].sum()), 0.0)
        self.assertEqual(int(m.F.max()), len(m) - 1)

    def test_transforms_move_normals_with_the_inverse_transpose(self):
        m = M.box(1, 1, 1).transformed(M.S(2, 1, 1))
        top = m.N[np.abs(m.N[:, 1] - 1) < 1e-9]
        self.assertTrue(np.allclose(top, [0, 1, 0]))
        self.assertAlmostEqual(float(m.P[:, 0].max()), 1.0)

    def test_compose_applies_the_last_matrix_first(self):
        p = M.compose(M.T(10, 0, 0), M.R((0, 1, 0), math.pi / 2)) @ np.array([1.0, 0, 0, 1])
        self.assertTrue(np.allclose(p[:3], [10, 0, -1]))                                  # rotate first (x to -z), then move


class Camera(unittest.TestCase):
    def forward(self, rot):
        x, y, z, a = rot
        return (M.R((x, y, z), a) @ np.array([0, 0, -1.0, 0]))[:3]

    def test_look_rotation_points_the_default_view_at_the_target(self):
        for eye, tgt in (((0, 0, 5), (0, 0, 0)), ((0, 0, 0), (5, 0, 0)), ((3, 2, 4), (-1, 0.5, -2)), ((0, 5, 0.01), (0, 0, 0)), ((0, 0, 0), (0, 0, 5))):
            f = np.asarray(tgt, float) - np.asarray(eye, float)
            f = f / np.linalg.norm(f)
            self.assertTrue(np.allclose(self.forward(M.look_rotation(eye, tgt)), f, atol=1e-6), (eye, tgt))

    def test_the_camera_keeps_its_up_vector_toward_plus_y(self):
        x, y, z, a = M.look_rotation((3, 2, 4), (-1, 0.5, -2))
        up = (M.R((x, y, z), a) @ np.array([0, 1.0, 0, 0]))[:3]
        self.assertGreater(up[1], 0.0)
        right = (M.R((x, y, z), a) @ np.array([1.0, 0, 0, 0]))[:3]
        self.assertAlmostEqual(float(right[1]), 0.0, places=6)                            # no roll


class Light(unittest.TestCase):
    def test_baked_light_falls_off_with_distance_and_respects_the_normal(self):
        floor = M.disc(1, 8, True)
        near = M.bake(floor.transformed(M.T(0, 0, 0)), albedo=(1, 1, 1), ambient=(0, 0, 0), sky=((0, 0, 0), (0, 0, 0)), lights=[((0, 1, 0), (1, 1, 1), 1.0, 1.0)])
        far = M.bake(floor, albedo=(1, 1, 1), ambient=(0, 0, 0), sky=((0, 0, 0), (0, 0, 0)), lights=[((0, 4, 0), (1, 1, 1), 1.0, 1.0)])
        under = M.bake(floor, albedo=(1, 1, 1), ambient=(0, 0, 0), sky=((0, 0, 0), (0, 0, 0)), lights=[((0, -1, 0), (1, 1, 1), 1.0, 1.0)])
        self.assertGreater(float(near.C[0].mean()), float(far.C[0].mean()))
        self.assertEqual(float(under.C.max()), 0.0)


class Nodes(unittest.TestCase):
    def test_geometry_writes_an_indexed_triangle_set_with_named_attributes(self):
        g = M.geometry(M.box().with_attr("note", [7.0]))
        x = g.xml()
        self.assertIn("<IndexedTriangleSet", x)
        self.assertIn("name='a_note'", x)
        self.assertIn("<Coordinate", x)
        self.assertEqual(M.geometry(M.box()).xml(), M.geometry(M.box()).xml())             # deterministic


class Attributes(unittest.TestCase):
    def test_a_number_or_short_vector_is_constant_and_a_column_is_per_vertex(self):
        m = M.box(1, 1, 1)
        n = len(m.P)
        self.assertEqual(m.with_attr("a", 2.5).attrs["a"].shape, (n, 1))
        self.assertEqual(m.with_attr("b", (1.0, 2.0, 3.0)).attrs["b"].shape, (n, 3))
        per = np.arange(n, dtype=float).reshape(-1, 1)
        got = m.with_attr("c", per).attrs["c"]
        self.assertEqual(got.shape, (n, 1))
        self.assertTrue(np.array_equal(got, per))

    def test_a_long_flat_array_is_refused_instead_of_becoming_a_huge_constant(self):
        """The bug this guards: a 1-D array of one number per vertex was tiled as a constant vector of n numbers, and the file declared numComponents of 84 (XSD maximum 4)."""
        m = M.box(1, 1, 1)
        with self.assertRaises(ValueError):
            m.with_attr("along", np.zeros(len(m.P)))
        with self.assertRaises(ValueError):
            m.with_attr("wide", np.zeros((len(m.P), 5)))
        with self.assertRaises(ValueError):
            m.with_attr("short", np.zeros((len(m.P) - 1, 1)))


if __name__ == "__main__":
    unittest.main()
