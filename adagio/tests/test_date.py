import unittest
from datetime import datetime

from adagio.utils.date import date_shift


class TestDate(unittest.TestCase):
    def setUp(self):
        self.t = datetime(2016, 8, 1)  # Monday

    def test_apply_offset(self):
        ans = datetime(2016, 8, 2)
        self.assertEqual(date_shift(self.t, "+1bd"), ans)

        ans = datetime(2016, 7, 25)
        self.assertEqual(date_shift(self.t, "-Mon"), ans)

        ans = datetime(2016, 8, 8)
        self.assertEqual(date_shift(self.t, "+Mon"), ans)

    def test_apply_offset_without_int(self):
        ans = datetime(2016, 8, 31)
        self.assertEqual(date_shift(self.t, "+MonthEnd"), ans)

    def test_multi_apply(self):
        ans = datetime(2016, 8, 26)
        self.assertEqual(date_shift(self.t, "+MonthEnd-3bd"), ans)
