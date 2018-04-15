import unittest

import adagio
from adagio import keys


class TestSingleEngine(unittest.TestCase):
    def setUp(self):
        longonly_params = {
            keys.lo_ticker: ['SGX_NK', 'LIFFE_FTI']
        }
        lo_vol_scale_params = {
            keys.vs_window: 63,
            keys.vs_chg_rule: '+Wed-1bd+1bd',
            keys.vs_target_vol: 0.1,
        }
        signal_params = {
            keys.signal_type: keys.momentum,
            keys.signal_windows: [[8, 24], [16, 48], [32, 96]],
            keys.signal_chg_rule: '+Wed-1bd+1bd',
            keys.signal_to_position: keys.linear,
            keys.position_cap: 1.0,
            keys.position_floor: -1.0
        }
        portfolio_params = {
            keys.weighting: keys.equal_weight
        }
        portfolio_vol_scale_params = {
            keys.vs_window: 63,
            keys.vs_chg_rule: '+Wed-1bd+1bd',
            keys.vs_target_vol: 0.1,
        }

        # Simple Engine example
        engine = adagio.Engine()
        engine.add(adagio.LongOnly(**longonly_params))
        engine.add(adagio.VolatilityScaling(**lo_vol_scale_params))
        engine.add(adagio.Signal(**signal_params))
        engine.add(adagio.Portfolio(**portfolio_params))
        engine.add(adagio.PortVolatilityScaling(**portfolio_vol_scale_params))
        engine.backtest()

        self.engine = engine

    def test_single_engine(self):
        self.assertEqual(len(self.engine), 5)
        self.assertEqual(len(self.engine[0]), 2)  # long only
        self.assertEqual(len(self.engine[1]), 2)  # vol scaling
        self.assertEqual(len(self.engine[2]), 2)  # signal
        self.assertEqual(len(self.engine[3]), 1)  # portfolio
        self.assertEqual(len(self.engine[4]), 1)  # portfolio vol scaling

        self.assertTrue(isinstance(self.engine[0][0], adagio.LongOnly))
        self.assertTrue(isinstance(self.engine[0][1], adagio.LongOnly))
        self.assertTrue(isinstance(self.engine[1][0], adagio.VolatilityScaling))
        self.assertTrue(isinstance(self.engine[1][1], adagio.VolatilityScaling))
        self.assertTrue(isinstance(self.engine[2][0], adagio.Signal))
        self.assertTrue(isinstance(self.engine[2][1], adagio.Signal))
        self.assertTrue(isinstance(self.engine[3][0], adagio.Portfolio))
        self.assertTrue(isinstance(self.engine[4][0],
                                   adagio.PortVolatilityScaling))

        position = self.engine[0][0].contracts[0].position
        self.assertEqual(position.columns[0], 'base')
        self.assertEqual(position.columns[1], 'volatility_scaling')
        self.assertEqual(position.columns[2], 'momentum')
        self.assertEqual(position.columns[3], 'portfolio')
        self.assertEqual(position.columns[4], 'portfolio_volatility_scaling')

    def test_longonly(self):

        longonly_params = {
            keys.lo_ticker: ['SGX_NK', 'LIFFE_FTI']
        }
        # Simple Engine example
        engine = adagio.Engine()
        engine.add(adagio.LongOnly(**longonly_params))
        engine.backtest()

        self.assertTrue(isinstance(self.engine[0][0], adagio.LongOnlyQuandlFutures))
        self.assertTrue(isinstance(self.engine[0][1], adagio.LongOnlyQuandlFutures))

    def test_longonly_quandlfutures(self):

        longonly_params = {
            keys.lo_ticker: ['SGX_NK', 'LIFFE_FTI']
        }
        # Simple Engine example
        engine = adagio.Engine()
        engine.add(adagio.LongOnlyQuandlFutures(**longonly_params))
        engine.backtest()

        self.assertTrue(isinstance(self.engine[0][0], adagio.LongOnlyQuandlFutures))
        self.assertTrue(isinstance(self.engine[0][1], adagio.LongOnlyQuandlFutures))


class TestMultipleEngine(unittest.TestCase):
    def setUp(self):
        longonly_params = {
            keys.lo_ticker: ['SGX_NK', 'LIFFE_FTI'],
        }
        lo_vol_scale_params = {
            keys.vs_window: 63,
            keys.vs_chg_rule: '+Wed-1bd+1bd',
            keys.vs_target_vol: 0.1,
        }
        signal_params = {
            keys.signal_type: keys.momentum,
            keys.signal_windows: [[8, 24], [16, 48], [32, 96]],
            keys.signal_chg_rule: '+Wed-1bd+1bd',
            keys.signal_to_position: keys.linear,
            keys.position_cap: 1.0,
            keys.position_floor: -1.0
        }
        portfolio_params = {
            keys.weighting: keys.equal_weight
        }
        portfolio_vol_scale_params = {
            keys.vs_window: 63,
            keys.vs_chg_rule: '+Wed-1bd+1bd',
            keys.vs_target_vol: 0.1,
        }

        # Nested Engine example
        engine1 = adagio.Engine()
        engine1.add(adagio.LongOnly(**longonly_params))
        engine1.add(adagio.VolatilityScaling(**lo_vol_scale_params))
        engine1.add(adagio.Signal(**signal_params))

        engine2 = adagio.Engine()
        engine2.add(adagio.LongOnly(**longonly_params))
        engine2.add(adagio.VolatilityScaling(**lo_vol_scale_params))
        engine2.add(adagio.Signal(**signal_params))

        engine3 = adagio.Engine()
        engine3.add([engine1, engine2])
        engine3.add(adagio.Portfolio(**portfolio_params))
        engine3.add(adagio.PortVolatilityScaling(**portfolio_vol_scale_params))
        engine3.backtest()

        self.engine = engine3

    def test_multiple_engines(self):
        self.assertEqual(len(self.engine), 3)
        self.assertEqual(len(self.engine[0]), 2)  # engines
        self.assertEqual(len(self.engine[1]), 1)  # portfolio
        self.assertEqual(len(self.engine[2]), 1)  # portfolio vol scaling

        self.assertEqual(len(self.engine[0][0]), 3)  # engine
        self.assertEqual(len(self.engine[0][0][0]), 2)  # long only
        self.assertEqual(len(self.engine[0][0][1]), 2)  # vol scaling
        self.assertEqual(len(self.engine[0][0][2]), 2)  # signal
        self.assertEqual(len(self.engine[0][1]), 3)  # engine
        self.assertEqual(len(self.engine[0][1][0]), 2)  # long only
        self.assertEqual(len(self.engine[0][1][1]), 2)  # vol scaling
        self.assertEqual(len(self.engine[0][1][2]), 2)  # signal

        self.assertTrue(isinstance(self.engine[0][0], adagio.Engine))
        self.assertTrue(isinstance(self.engine[0][1], adagio.Engine))
        self.assertTrue(isinstance(self.engine[1][0], adagio.Portfolio))
        self.assertTrue(isinstance(self.engine[2][0],
                                   adagio.PortVolatilityScaling))

        self.assertTrue(isinstance(self.engine[0][0][0][0], adagio.LongOnly))
        self.assertTrue(isinstance(self.engine[0][0][0][1], adagio.LongOnly))
        self.assertTrue(isinstance(self.engine[0][0][1][0],
                                   adagio.VolatilityScaling))
        self.assertTrue(isinstance(self.engine[0][0][1][1],
                                   adagio.VolatilityScaling))
        self.assertTrue(isinstance(self.engine[0][0][2][0], adagio.Signal))
        self.assertTrue(isinstance(self.engine[0][0][2][1], adagio.Signal))

        self.assertTrue(isinstance(self.engine[0][1][0][0], adagio.LongOnly))
        self.assertTrue(isinstance(self.engine[0][1][0][1], adagio.LongOnly))
        self.assertTrue(isinstance(self.engine[0][1][1][0],
                                   adagio.VolatilityScaling))
        self.assertTrue(isinstance(self.engine[0][1][1][1],
                                   adagio.VolatilityScaling))
        self.assertTrue(isinstance(self.engine[0][1][2][0], adagio.Signal))
        self.assertTrue(isinstance(self.engine[0][1][2][1], adagio.Signal))

        position = self.engine[0][0][0][0].contracts[0].position
        self.assertEqual(position.columns[0], 'base')
        self.assertEqual(position.columns[1], 'volatility_scaling')
        self.assertEqual(position.columns[2], 'momentum')
        self.assertEqual(position.columns[3], 'portfolio')
        self.assertEqual(position.columns[4], 'portfolio_volatility_scaling')

        engine1_ret = self.engine[0][0].get_final_gross_returns().sum()
        engine2_ret = self.engine[0][1].get_final_gross_returns().sum()
        self.assertAlmostEqual(engine1_ret, engine2_ret)
        self.assertAlmostEqual(self.engine.get_final_gross_returns().sum(),
                               engine1_ret + engine2_ret)
