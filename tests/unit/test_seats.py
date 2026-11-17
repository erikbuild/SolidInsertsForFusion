# ABOUTME: Unit tests for SolidInserts seat planning: sizing each selected opening, the checks
# ABOUTME: that block or warn about a seat, batch overlap, and the dialog summary lines.
import unittest

from SolidInserts.catalog import AUTOMATIC, Series
from SolidInserts.seats import Opening, plan_seats, summary_html, summary_lines


def opening(ordinal=1, body='Plate', plane='top', center=(10.0, 10.0, 18.0), outward=(0.0, 0.0, 1.0),
            diameter=3.0, bore_depth=7.0, can_deepen=True, clearance=10.0):
    return Opening(ordinal=ordinal, body_key=body, body_name=body, plane_key=plane, center=center,
                   outward=outward, diameter=diameter, bore_depth=bore_depth, can_deepen=can_deepen,
                   clearance=clearance)


M3 = opening()
M4 = opening(ordinal=2, center=(30.0, 10.0, 18.0), diameter=4.0, bore_depth=18.0, can_deepen=False)


def plan(*openings, series=Series.STANDARD, thread=AUTOMATIC, compensation=0.0, rim_errors=(), chamfer=None):
    return plan_seats(openings, series, thread, compensation, rim_errors, chamfer_mm=chamfer)


class PlanSeatsTest(unittest.TestCase):
    def test_automatic_sizes_each_hole(self):
        result = plan(M3, M4)
        self.assertEqual(
            [(s.insert.thread, s.diameter, s.depth, s.name, s.wall) for s in result.seats],
            [('M3 × 0.50', 4.0, 6.7, 'Insert M3 × 5.7', 8.0),
             ('M4 × 0.70', 5.7, 9.1, 'Insert M4 × 8.1', 7.15)])
        self.assertEqual(result.obstacles, ())
        self.assertEqual(result.notes, ())
        self.assertTrue(result.can_apply)

    def test_compensation_changes_only_the_diameter(self):
        seat, = plan(M3, compensation=0.1).seats
        self.assertEqual((seat.diameter, seat.depth), (4.1, 6.7))

    def test_compensation_out_of_range(self):
        result = plan(M3, compensation=1.5)
        self.assertIn('Diameter compensation must be between −1 and +1 mm.', result.obstacles)
        self.assertFalse(result.can_apply)

    def test_same_opening_twice_makes_one_seat(self):
        self.assertEqual(len(plan(M3, opening(ordinal=2)).seats), 1)

    def test_automatic_needs_a_recognised_hole(self):
        unrecognised_hole = opening(diameter=3.3)
        self.assertEqual(plan(unrecognised_hole).obstacles,
                         ('Hole 1 on Plate. Hole Ø3.30 mm. Select the screw thread explicitly.',))
        self.assertEqual(plan(unrecognised_hole, thread='M3 × 0.50').seats[0].diameter, 4.0)

    def test_automatic_clearance_hole_plans_a_seat(self):
        result = plan(opening(diameter=3.2))
        self.assertEqual([(s.insert.thread, s.diameter) for s in result.seats], [('M3 × 0.50', 4.0)])
        self.assertEqual(result.obstacles, ())

    def test_coarse_clearance_wider_than_the_seat(self):
        self.assertEqual(plan(opening(diameter=12.0)).obstacles,
                         ('Hole 1 on Plate. The Ø12.00 seat must be wider than the Ø12.00 mm hole.',))

    def test_seat_must_be_wider_than_the_hole(self):
        self.assertEqual(plan(opening(diameter=4.0), thread='M3 × 0.50').obstacles,
                         ('Hole 1 on Plate. The Ø4.00 seat must be wider than the Ø4.00 mm hole.',))

    def test_seat_reaching_an_edge(self):
        self.assertEqual(plan(opening(clearance=2.0)).obstacles,
                         ('Hole 1 on Plate. The Ø4.00 seat reaches a nearby edge at the opening.',))

    def test_thin_wall_is_a_note(self):
        result = plan(opening(clearance=2.5))
        self.assertEqual(result.notes, ('Hole 1 on Plate. The opening has 0.50 mm of material to the nearest '
                                        'edge. The catalog specifies 1.60 mm.',))
        self.assertTrue(result.can_apply)

    def test_seat_deeper_than_the_bore(self):
        shallow_through = opening(bore_depth=5.0, can_deepen=False)
        self.assertEqual(plan(shallow_through).obstacles,
                         ('Hole 1 on Plate. The seat needs 6.70 mm of depth. The cylindrical wall ends at '
                          '5.00 mm; choose a shorter insert.',))
        self.assertEqual(plan(shallow_through, series=Series.SHORT).obstacles, ())
        self.assertEqual(plan(opening(bore_depth=4.0, can_deepen=True)).obstacles, ())

    def test_overlapping_seats(self):
        first = opening(center=(40.0, 20.0, 18.0))
        second = opening(ordinal=2, center=(43.5, 20.0, 18.0))
        self.assertEqual(plan(first, second).obstacles,
                         ('The seats for holes 1 and 2 overlap at the opening.',))
        self.assertEqual(plan(first, opening(ordinal=2, body='Other', center=(43.5, 20.0, 18.0))).obstacles, ())
        self.assertEqual(plan(first, opening(ordinal=2, center=(43.5, 20.0, 18.0),
                                             outward=(0.0, 0.0, -1.0))).obstacles, ())

    def test_chamfer_is_carried_on_each_seat(self):
        chamfered, = plan(M3, chamfer=0.4).seats
        plain, = plan(M3).seats
        self.assertEqual((chamfered.chamfer, chamfered.mouth_diameter), (0.4, 4.8))
        self.assertEqual((plain.chamfer, plain.mouth_diameter), (None, 4.0))

    def test_chamfer_reaching_an_edge(self):
        self.assertEqual(plan(opening(clearance=2.3), chamfer=0.4).obstacles,
                         ('Hole 1 on Plate. The 0.40 mm chamfer on the Ø4.00 seat reaches a nearby edge '
                          'at the opening.',))
        self.assertEqual(plan(opening(clearance=2.3)).obstacles, ())

    def test_a_seat_reaching_an_edge_names_only_the_seat(self):
        self.assertEqual(plan(opening(clearance=2.0), chamfer=0.4).obstacles,
                         ('Hole 1 on Plate. The Ø4.00 seat reaches a nearby edge at the opening.',))

    def test_overlapping_chamfers(self):
        first = opening(center=(40.0, 20.0, 18.0))
        second = opening(ordinal=2, center=(44.5, 20.0, 18.0))
        self.assertEqual(plan(first, second, chamfer=0.4).obstacles,
                         ('The chamfers of the seats for holes 1 and 2 overlap at the opening.',))
        self.assertEqual(plan(first, second).obstacles, ())

    def test_overlapping_seats_name_only_the_seats(self):
        first = opening(center=(40.0, 20.0, 18.0))
        second = opening(ordinal=2, center=(43.5, 20.0, 18.0))
        self.assertEqual(plan(first, second, chamfer=0.4).obstacles,
                         ('The seats for holes 1 and 2 overlap at the opening.',))

    def test_chamfer_out_of_range(self):
        for chamfer in (0.05, 2.5):
            result = plan(M3, chamfer=chamfer)
            self.assertIn('Chamfer size must be between 0.10 and 2.00 mm.', result.obstacles)
            self.assertFalse(result.can_apply)
        for chamfer in (0.1, 2.0):
            self.assertEqual(plan(M3, chamfer=chamfer).obstacles, ())

    def test_thin_wall_note_ignores_the_chamfer(self):
        result = plan(opening(clearance=2.5), chamfer=0.4)
        self.assertEqual(result.notes, plan(opening(clearance=2.5)).notes)
        self.assertEqual(result.notes, ('Hole 1 on Plate. The opening has 0.50 mm of material to the nearest '
                                        'edge. The catalog specifies 1.60 mm.',))
        self.assertEqual(result.obstacles, ())

    def test_rim_errors_come_first(self):
        result = plan(opening(clearance=2.0), rim_errors=('Hole 3 on Plate. X',))
        self.assertEqual(result.obstacles[0], 'Hole 3 on Plate. X')
        self.assertFalse(result.can_apply)

    def test_nothing_selected(self):
        self.assertEqual(plan().obstacles, ('Select the circular rim of each hole in the 3D view.',))


class SummaryLinesTest(unittest.TestCase):
    def test_lists_each_seat(self):
        self.assertEqual(summary_lines(plan(M3, M4)),
                         ['Hole 1 · M3 × 0.50 · Ø4.00 × 6.70 mm', 'Hole 2 · M4 × 0.70 · Ø5.70 × 9.10 mm'])

    def test_lists_each_seat_with_its_chamfer(self):
        self.assertEqual(summary_lines(plan(M3, chamfer=0.4)),
                         ['Hole 1 · M3 × 0.50 · Ø4.00 × 6.70 mm · 0.40 mm chamfer'])

    def test_obstacles_then_notes(self):
        lines = summary_lines(plan(opening(clearance=2.5), opening(ordinal=2, diameter=3.3,
                                                                     center=(30.0, 10.0, 18.0))))
        self.assertEqual(lines, [
            'Hole 1 · M3 × 0.50 · Ø4.00 × 6.70 mm',
            'Hole 2 on Plate. Hole Ø3.30 mm. Select the screw thread explicitly.',
            'Note: Hole 1 on Plate. The opening has 0.50 mm of material to the nearest edge. '
            'The catalog specifies 1.60 mm.',
        ])

    def test_html_escapes_each_line_and_breaks_between_them(self):
        self.assertEqual(summary_html(plan(M3, rim_errors=('Hole 2 on A&B <1>. X.',))),
                         'Hole 1 · M3 × 0.50 · Ø4.00 × 6.70 mm<br>Hole 2 on A&amp;B &lt;1&gt;. X.')


if __name__ == '__main__':
    unittest.main()
