# ABOUTME: Unit tests for the openings cache: one model read per selection, a fresh read when the
# ABOUTME: selection changes or is cleared, and no remembered selection after a failed read.
import unittest

from SolidInserts.openings_cache import OpeningsCache


class OpeningsCacheTest(unittest.TestCase):
    def setUp(self):
        self.calls = []

    def read_openings(self, design, rims):
        self.calls.append(list(rims))
        return ['opening {}'.format(rim) for rim in rims], []

    def test_the_same_selection_is_read_once(self):
        cache = OpeningsCache(self.read_openings)
        first = cache.read('design', ['a', 'b'])
        self.assertEqual(cache.read('design', ['a', 'b']), first)
        self.assertEqual(self.calls, [['a', 'b']])

    def test_a_changed_selection_is_read_again(self):
        cache = OpeningsCache(self.read_openings)
        cache.read('design', ['a'])
        self.assertEqual(cache.read('design', ['a', 'b']), (['opening a', 'opening b'], []))
        self.assertEqual(self.calls, [['a'], ['a', 'b']])

    def test_clear_forgets_the_selection(self):
        cache = OpeningsCache(self.read_openings)
        cache.read('design', ['a'])
        cache.clear()
        cache.read('design', ['a'])
        self.assertEqual(self.calls, [['a'], ['a']])

    def test_a_failed_read_is_not_remembered_for_its_selection(self):
        def read_openings(design, rims):
            if len(self.calls) == 1:
                self.calls.append(list(rims))
                raise RuntimeError('unreadable rim')
            return self.read_openings(design, rims)

        cache = OpeningsCache(read_openings)
        cache.read('design', ['a'])
        with self.assertRaises(RuntimeError):
            cache.read('design', ['a', 'b'])
        self.assertEqual(cache.read('design', ['a', 'b']), (['opening a', 'opening b'], []))
        self.assertEqual(self.calls, [['a'], ['a', 'b'], ['a', 'b']])


if __name__ == '__main__':
    unittest.main()
