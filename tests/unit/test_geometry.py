# ABOUTME: Unit tests for SolidInserts hole geometry rules: recognising a hole entrance,
# ABOUTME: finding where the bore ends, and checking a finished cut's direction, volume and floor.
import math
import unittest

from SolidInserts.geometry import (BoreEdge, Circle, Cylinder, PlanarFace, bore_end, cut_direction,
                                   cut_volume_matches, expected_cut_volume_mm3, is_floor,
                                   is_hole_entrance, round_mm)

UP = (0.0, 0.0, 1.0)
DOWN = (0.0, 0.0, -1.0)
TOP_RIM = Circle((8.0, 8.0, 18.0), UP, 1.5)
WALL = Cylinder((8.0, 8.0, 0.0), UP, 1.5)
WALL_POINT = (9.5, 8.0, 15.0)
TOWARD_AXIS = (-1.0, 0.0, 0.0)


class HoleEntranceTest(unittest.TestCase):
    def test_top_rim_of_a_hole(self):
        self.assertTrue(is_hole_entrance(TOP_RIM, UP, WALL, WALL_POINT, TOWARD_AXIS))

    def test_bottom_rim_of_a_through_hole(self):
        self.assertTrue(is_hole_entrance(
            Circle((23.0, 9.0, 0.0), DOWN, 2.0), DOWN,
            Cylinder((23.0, 9.0, 0.0), UP, 2.0), (25.0, 9.0, 5.0), TOWARD_AXIS))

    def test_boss_rim_is_convex(self):
        self.assertFalse(is_hole_entrance(TOP_RIM, UP, WALL, WALL_POINT, (1.0, 0.0, 0.0)))

    def test_blind_hole_floor_rim_has_the_wall_outside(self):
        floor_rim = Circle((8.0, 8.0, 11.0), UP, 1.5)
        self.assertFalse(is_hole_entrance(floor_rim, UP, WALL, WALL_POINT, TOWARD_AXIS))

    def test_wall_radius_must_match(self):
        self.assertFalse(is_hole_entrance(
            TOP_RIM, UP, Cylinder((8.0, 8.0, 0.0), UP, 2.0), (10.0, 8.0, 15.0), TOWARD_AXIS))

    def test_wall_axis_must_be_parallel(self):
        self.assertFalse(is_hole_entrance(
            TOP_RIM, UP, Cylinder((8.0, 8.0, 0.0), (0.0, 1.0, 0.0), 1.5), WALL_POINT, TOWARD_AXIS))

    def test_rim_centre_must_be_on_the_axis(self):
        self.assertFalse(is_hole_entrance(
            Circle((8.1, 8.0, 18.0), UP, 1.5), UP, WALL, WALL_POINT, TOWARD_AXIS))


class BoreEndTest(unittest.TestCase):
    def test_blind_hole_with_flat_floor(self):
        floor = BoreEdge(Circle((8.0, 8.0, 11.0), UP, 1.5), (PlanarFace(UP, math.pi * 2.25),))
        self.assertEqual(bore_end(TOP_RIM, UP, [floor]), (7.0, True))

    def test_through_hole(self):
        rim = Circle((23.0, 9.0, 18.0), UP, 2.0)
        bottom = BoreEdge(Circle((23.0, 9.0, 0.0), DOWN, 2.0), (PlanarFace(DOWN, 1200.0),))
        self.assertEqual(bore_end(rim, UP, [bottom]), (18.0, False))

    def test_annular_floor_cannot_be_deepened(self):
        floor = BoreEdge(Circle((8.0, 8.0, 11.0), UP, 1.5), (PlanarFace(UP, 5.0),))
        self.assertEqual(bore_end(TOP_RIM, UP, [floor]), (7.0, False))

    def test_nearest_end_wins(self):
        deep = BoreEdge(Circle((8.0, 8.0, 6.0), UP, 1.5), ())
        near = BoreEdge(Circle((8.0, 8.0, 11.0), UP, 1.5), ())
        self.assertEqual(bore_end(TOP_RIM, UP, [deep, near]), (7.0, False))

    def test_unrelated_edges_are_ignored(self):
        self.assertIsNone(bore_end(TOP_RIM, UP, [
            BoreEdge(Circle((8.0, 8.0, 11.0), UP, 2.0), ()),
            BoreEdge(Circle((8.5, 8.0, 11.0), UP, 1.5), ()),
            BoreEdge(TOP_RIM, ()),
        ]))


class CutTest(unittest.TestCase):
    def test_expected_cut_volume(self):
        self.assertAlmostEqual(expected_cut_volume_mm3(4.0, 6.7, 3.0, 7.0), 36.835, places=3)
        self.assertAlmostEqual(expected_cut_volume_mm3(5.7, 9.1, 4.0, 18.0), 117.856, places=3)
        self.assertAlmostEqual(expected_cut_volume_mm3(4.0, 6.7, 3.0, 4.0), 55.920, places=3)

    def test_cut_volume_tolerance(self):
        self.assertTrue(cut_volume_matches(36.853, 36.835))
        self.assertFalse(cut_volume_matches(36.816, 36.835))

    def test_cut_direction_follows_the_sketch_normal(self):
        self.assertEqual(cut_direction((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), DOWN), -1)
        self.assertEqual(cut_direction((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), UP), 1)

    def test_floor_at_depth(self):
        self.assertTrue(is_floor((8.0, 8.0, 11.3), UP, (8.0, 8.0, 18.0), UP, 6.7))
        self.assertFalse(is_floor((8.0, 8.0, 11.3), UP, (8.0, 8.0, 18.0), UP, 6.0))
        self.assertFalse(is_floor((8.0, 8.0, 11.3), DOWN, (8.0, 8.0, 18.0), UP, 6.7))

    def test_round_mm_keeps_three_decimals(self):
        self.assertEqual(round_mm(4.1004), 4.1)


if __name__ == '__main__':
    unittest.main()
