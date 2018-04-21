import unittest

import adagio
from adagio.layers.longonly import LongOnlyQuandlFutures
from adagio.utils import keys
from adagio.utils.const import FuturesInfo, DEFAULT_ROLL_RULE


class TestLongOnly(unittest.TestCase):
    def setUp(self):
        # Simple Engine example
        engine = adagio.Engine()
        engine.add(adagio.LongOnly(lo_ticker='CME_ES'))
        engine.backtest()

        self.engine = engine
        self.contract = engine[0][0].contracts[0]

    def test_backtest_ccy(self):
        futures = FuturesInfo.EUREX_FDAX
        futures_info = futures.value._asdict()
        futures_info[keys.lo_ticker] = futures.name

        longonly = LongOnlyQuandlFutures(**futures_info)
        self.assertEqual(longonly[keys.backtest_ccy],
                         futures_info[keys.contract_ccy])

    def test_start_from(self):
        self.assertEqual(self.contract[keys.start_from],
                         FuturesInfo.CME_ES.value.start_from)

    def test_roll_date_position(self):
        position = self.contract.get_final_positions()
        roll_date = self.contract.get_roll_date(DEFAULT_ROLL_RULE)
        self.assertEqual(position[roll_date], 1)
        self.assertEqual(position.shift(-1)[roll_date], 0)

    def test_nth_contract(self):
        engine = adagio.Engine()
        engine.add(adagio.LongOnly(lo_ticker='CME_ES', nth_contract=2))
        engine.backtest()

        roll_date = self.contract.get_roll_date(DEFAULT_ROLL_RULE)
        contract2 = engine[0][0].contracts[0]
        position = contract2.get_final_positions()
        self.assertEqual(position[roll_date], 1)
        self.assertEqual(position.shift(-1)[roll_date], 0)
        self.assertEqual(len(self.engine[0][0].contracts) - 1,
                         len(engine[0][0].contracts))
