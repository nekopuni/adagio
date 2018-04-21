from datetime import datetime
import unittest

import adagio


class TestContract(unittest.TestCase):
    def setUp(self):
        # Simple Engine example
        engine = adagio.Engine()
        engine.add(adagio.LongOnly(lo_ticker='CME_ES'))
        engine.backtest()

        self.engine_es = engine
        self.contract_es = self.engine_es[0][0].contracts[0]

        engine = adagio.Engine()
        engine.add(adagio.LongOnly(lo_ticker='CME_TY'))
        engine.backtest()

        self.engine_ty = engine
        self.contract_ty = self.engine_ty[0][0].contracts[0]

    def test_get_roll_date(self):
        # CME/ESZ1997
        self.assertEqual(self.contract_es.roll_date, datetime(1997, 12, 16))
        # CME/TYM1990 - uses first notice date
        self.assertEqual(self.contract_ty.roll_date, datetime(1990, 5, 28))
