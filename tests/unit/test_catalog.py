# ABOUTME: Unit tests for the CNC Kitchen insert catalog: thread choice from hole size,
# ABOUTME: per-series seat dimensions, product names and unavailable combinations.
import unittest

from SolidInserts.catalog import AUTOMATIC, THREAD_CHOICES, Series, choose
from SolidInserts.messages import SeatError

# CNC Kitchen, Dimensions & Design Guidelines, except the VORON seat diameter, which is the Ø4.6 mm
# insert hole in Voron Design's Downdraft toolhead CAD: (series, thread) -> (L, D2, W) in mm.
CATALOG = {
    (Series.STANDARD, 'M1.6 × 0.35'): (2.5, 2.2, 1.3),
    (Series.STANDARD, 'M2 × 0.40'): (3.0, 3.2, 1.3),
    (Series.STANDARD, 'M2.5 × 0.45'): (4.0, 4.0, 1.6),
    (Series.STANDARD, 'M3 × 0.50'): (5.7, 4.0, 1.6),
    (Series.STANDARD, 'M4 × 0.70'): (8.1, 5.7, 2.1),
    (Series.STANDARD, 'M5 × 0.80'): (9.5, 6.5, 2.6),
    (Series.STANDARD, 'M6 × 1.00'): (12.7, 8.1, 3.3),
    (Series.STANDARD, 'M8 × 1.25'): (12.7, 9.7, 4.5),
    (Series.STANDARD, 'M10 × 1.50'): (12.7, 12.0, 6.0),
    (Series.SHORT, 'M3 × 0.50'): (3.0, 4.0, 1.6),
    (Series.SHORT, 'M4 × 0.70'): (4.0, 5.7, 2.1),
    (Series.SHORT, 'M5 × 0.80'): (5.8, 6.5, 2.6),
    (Series.SHORT, 'M6 × 1.00'): (6.8, 8.1, 3.3),
    (Series.SHORT, 'M8 × 1.25'): (6.8, 9.7, 4.5),
    (Series.VORON, 'M3 × 0.50'): (4.0, 4.6, 1.6),
}


class ChooseTest(unittest.TestCase):
    def test_hole_selects_the_thread_but_series_sets_the_seat(self):
        for series, bore, depth in [(Series.STANDARD, 4.0, 6.7),
                                    (Series.SHORT, 4.0, 4.0),
                                    (Series.VORON, 4.6, 5.0)]:
            insert = choose(series, AUTOMATIC, 3.0 - 1e-12)
            self.assertEqual(insert.thread, 'M3 × 0.50')
            self.assertEqual(insert.bore_mm, bore)
            self.assertAlmostEqual(insert.depth_mm, depth, places=9)

    def test_automatic_accepts_the_tolerance_edge(self):
        self.assertEqual(choose(Series.STANDARD, AUTOMATIC, 2.55).thread, 'M2.5 × 0.45')

    def test_automatic_finds_m1_6(self):
        self.assertEqual(choose(Series.STANDARD, AUTOMATIC, 1.6).thread, 'M1.6 × 0.35')

    def test_automatic_rejects_clearance_holes(self):
        with self.assertRaises(SeatError) as raised:
            choose(Series.STANDARD, AUTOMATIC, 3.2)
        self.assertEqual(str(raised.exception), 'Hole Ø3.20 mm. Select the screw thread explicitly.')
        with self.assertRaises(SeatError):
            choose(Series.STANDARD, AUTOMATIC, 4.5)

    def test_manual_thread_outside_the_series_is_refused(self):
        with self.assertRaises(SeatError) as raised:
            choose(Series.VORON, 'M4 × 0.70', 4.0)
        self.assertEqual(str(raised.exception),
                         'M4 × 0.70 is not available in the CNC Kitchen VORON M3 × 5 × 4 series.')

    def test_manual_thread_ignores_the_hole_size(self):
        self.assertEqual(choose(Series.STANDARD, 'M3 × 0.50', 3.2).bore_mm, 4.0)

    def test_every_catalog_row(self):
        for (series, thread), (length, bore, wall) in CATALOG.items():
            insert = choose(series, thread, 0.0)
            self.assertEqual((insert.length_mm, insert.bore_mm, insert.wall_mm), (length, bore, wall),
                             (series, thread))

    def test_catalog_has_exactly_these_rows(self):
        for series in Series:
            for thread in THREAD_CHOICES[1:]:
                if (series, thread) in CATALOG:
                    self.assertEqual(choose(series, thread, 0.0).thread, thread)
                else:
                    with self.assertRaises(SeatError, msg=(series, thread)):
                        choose(series, thread, 0.0)

    def test_product_names(self):
        self.assertEqual(choose(Series.STANDARD, 'M3 × 0.50', 3.0).product_name, 'M3 × 5.7')
        self.assertEqual(choose(Series.SHORT, 'M3 × 0.50', 3.0).product_name, 'M3 × 3 (Short Version)')
        self.assertEqual(choose(Series.VORON, 'M3 × 0.50', 3.0).product_name, 'VORON M3 × 5 × 4')
        self.assertEqual(choose(Series.STANDARD, 'M10 × 1.50', 10.0).product_name, 'M10 × 12.7')
        self.assertEqual(choose(Series.STANDARD, 'M1.6 × 0.35', 1.6).product_name, 'M1.6 × 2.5')
        self.assertEqual(choose(Series.SHORT, 'M6 × 1.00', 6.0).product_name, 'M6 × 6.8 (Short Version)')


class ChoicesTest(unittest.TestCase):
    def test_thread_choices_start_with_automatic(self):
        self.assertEqual(THREAD_CHOICES, (
            'Automatic (nominal Ø)', 'M1.6 × 0.35', 'M2 × 0.40', 'M2.5 × 0.45', 'M3 × 0.50', 'M4 × 0.70',
            'M5 × 0.80', 'M6 × 1.00', 'M8 × 1.25', 'M10 × 1.50'))

    def test_series_order_and_labels(self):
        self.assertEqual([s.value for s in Series],
                         ['Standard', 'Short Version', 'VORON M3 × 5 × 4'])


if __name__ == '__main__':
    unittest.main()
