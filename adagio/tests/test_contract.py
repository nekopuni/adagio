from datetime import datetime
import unittest

import adagio


class TestContract(unittest.TestCase):
    def setUp(self):
        # Simple Engine example
        engine = adagio.Engine()
        engine.add(adagio.LongOnly(lo_ticker='CME_SP'))
        engine.backtest()

        self.engine_sp = engine
        self.contract_sp = self.engine_sp[0][0].contracts[0]

        engine = adagio.Engine()
        engine.add(adagio.LongOnly(lo_ticker='CME_TY'))
        engine.backtest()

        self.engine_ty = engine
        self.contract_ty = self.engine_ty[0][0].contracts[0]

    def test_get_roll_date(self):
        # CME/SPM1982
        self.assertEqual(self.contract_sp.roll_date, datetime(1982, 6, 15))
        # CME/TYM1990 - uses first notice date
        self.assertEqual(self.contract_ty.roll_date, datetime(1990, 5, 28))
