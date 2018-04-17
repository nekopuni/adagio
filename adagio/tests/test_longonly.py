import unittest

from adagio.layers.longonly import LongOnlyQuandlFutures
from adagio.utils import keys
from adagio.utils.const import FuturesInfo


class TestLongOnly(unittest.TestCase):
    def test_backtest_ccy(self):
        futures = FuturesInfo.EUREX_FDAX
        futures_info = futures.value._asdict()
        futures_info[keys.lo_ticker] = futures.name

        longonly = LongOnlyQuandlFutures(**futures_info)
        self.assertEqual(longonly[keys.backtest_ccy],
                         futures_info[keys.contract_ccy])