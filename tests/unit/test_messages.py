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

    def test_seat_error_carries_the_copy(self):
        self.assertEqual(str(SeatError(message('select_rims'))),
                         'Select the circular rim of each hole in the 3D view.')


if __name__ == '__main__':
    unittest.main()
