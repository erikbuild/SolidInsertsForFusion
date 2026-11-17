# ABOUTME: Unit tests for SolidInserts user-facing copy: template filling and
# ABOUTME: rejection of unknown message keys.
import unittest

from SolidInserts.messages import SeatError, message


class MessageTest(unittest.TestCase):
    def test_seat_line_formats_thread_diameter_and_depth(self):
        self.assertEqual(
            message('seat_line', ordinal=1, thread='M3 × 0.50', diameter=4, depth=6.7),
            'Hole 1 · M3 × 0.50 · Ø4.00 × 6.70 mm')

    def test_hole_prefix_names_the_hole_and_body(self):
        self.assertEqual(
            message('hole_prefix', ordinal=2, body='Plate', reason='X.'),
            'Hole 2 on Plate. X.')

    def test_unknown_key_raises(self):
        with self.assertRaises(KeyError):
            message('nope')

    def test_dialog_copy_names_the_command_and_its_inputs(self):
        expected = {
            'command_name': 'Insert Seats',
            'command_tooltip': 'Cut seats for heat-set threaded inserts at the rims of existing holes.',
            'holes_label': 'Holes',
            'series_label': 'Type',
            'series_tooltip': 'Short Version for M3, M4, M5, M6 and M8. VORON M3 × 5 × 4 for M3.',
            'thread_label': 'Screw thread',
            'thread_tooltip': ('Automatic matches the nominal hole diameter within ±0.05 mm. '
                               'For clearance holes, choose the screw size.'),
            'compensation_label': 'Diameter compensation',
            'compensation_tooltip': 'Adjustment to the seat diameter. Use 0 for the catalog dimension.',
            'chamfer_label': 'Chamfer top edge',
            'chamfer_tooltip': 'Adds a 45° lead-in at the seat opening so the insert starts straight.',
            'chamfer_size_label': 'Chamfer size',
            'chamfer_size_tooltip': 'How far the chamfer cuts into the face and down the seat wall.',
            'summary_label': 'Seats',
        }
        self.assertEqual({key: message(key) for key in expected}, expected)

    def test_unexpected_error_includes_the_details(self):
        self.assertEqual(message('unexpected_error', details='Traceback'),
                         'SolidInserts stopped because of an unexpected error:\nTraceback')

    def test_seat_error_carries_the_copy(self):
        self.assertEqual(str(SeatError(message('select_rims'))),
                         'Select the circular rim of each hole in the 3D view.')


if __name__ == '__main__':
    unittest.main()
