import unittest

from adagio.utils.array import is_flat_list, is_2d_list


class TestArray(unittest.TestCase):
    def test_is_flat_list(self):
        self.assertTrue(is_flat_list([1, 2, 3]))

        self.assertFalse(is_flat_list(1))
        self.assertFalse(is_flat_list([[1, 2], [3, 4]]))

    def test_is_2d_list(self):
        self.assertTrue(is_2d_list([[1, 2], [3, 4]]))

        self.assertFalse(is_2d_list(1))
        self.assertFalse(is_2d_list([1, 2, 3]))
