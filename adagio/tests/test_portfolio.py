import unittest

import adagio
from adagio import keys


class TestEqualWeight(unittest.TestCase):
    def setUp(self):
        longonly_params = {
            keys.lo_ticker: ['SGX_NK', 'LIFFE_FTI']
        }
        portfolio_params = {
            keys.weighting: keys.equal_weight,
            keys.port_weight_chg_rule: '+Wed-1bd+1bd',
        }

        # Simple Engine example
        engine = adagio.Engine()
        engine.add(adagio.LongOnly(**longonly_params))
        engine.add(adagio.Portfolio(**portfolio_params))
        engine.backtest()

        self.engine = engine

    def test_equal_weight(self):
        self.assertAlmostEqual(self.engine[0][0].contracts[0]
                               .position['portfolio'][-1], 0.5)
        self.assertAlmostEqual(self.engine[0][1].contracts[0]
                               .position['portfolio'][-1], 0.5)


class TestFixedWeight(unittest.TestCase):
    def setUp(self):
        longonly_params = {
            keys.lo_ticker: ['SGX_NK', 'LIFFE_FTI']
        }
        portfolio_params = {
            keys.weighting: [0.1, 0.9]
        }

        # Simple Engine example
        engine = adagio.Engine()
        engine.add(adagio.LongOnly(**longonly_params))
        engine.add(adagio.Portfolio(**portfolio_params))
        engine.backtest()

        self.engine = engine

    def test_equal_weight(self):
        self.assertAlmostEqual(self.engine[0][0].contracts[0]
                               .position['portfolio'][0], 0.1)
        self.assertAlmostEqual(self.engine[0][1].contracts[0]
                               .position['portfolio'][0], 0.9)
