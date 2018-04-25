from datetime import datetime
import unittest

import adagio
from adagio import keys
from adagio.layers.longonly import LongOnlyQuandlFutures


class TestSingleEngine(unittest.TestCase):
    def setUp(self):
        longonly_params = {
            keys.lo_ticker: ['SGX_NK', 'LIFFE_FTI']
        }
        lo_vol_scale_params = {
            keys.vs_chg_rule: '+Wed-1bd+1bd',
            keys.vs_target_vol: 0.1,
            keys.vs_method_params: {
                keys.vs_method: keys.vs_rolling,
                keys.vs_window: 63,
            }
        }
        signal_params = {
            keys.signal_method_params: {
                keys.signal_method: keys.signal_trend_ma_xover,
                keys.signal_windows: [[8, 24], [16, 48], [32, 96]],
            },
            keys.signal_chg_rule: '+Wed-1bd+1bd',
            keys.signal_to_position: keys.linear,
            keys.position_cap: 1.0,
            keys.position_floor: -1.0
        }
        portfolio_params = {
            keys.weighting: keys.equal_weight,
            keys.port_weight_chg_rule: '+Wed-1bd+1bd',
        }
        portfolio_vol_scale_params = {
            keys.vs_chg_rule: '+Wed-1bd+1bd',
            keys.vs_target_vol: 0.1,
            keys.vs_method_params: {
                keys.vs_method: keys.vs_rolling,
                keys.vs_window: 63,
            }
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

        self.assertTrue(isinstance(self.engine[0][0], LongOnlyQuandlFutures))
        self.assertTrue(isinstance(self.engine[0][1], LongOnlyQuandlFutures))
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
        self.assertEqual(position.columns[2], 'signal_trend_ma_xover')
        self.assertEqual(position.columns[3], 'portfolio')
        self.assertEqual(position.columns[4], 'portfolio_volatility_scaling')

        self.assertEqual(self.engine.backtest_params[keys.backtest_ccy], 'USD')


class TestBacktestPreiod(unittest.TestCase):
    def test_start_end_date(self):
        engine = adagio.Engine()
        self.assertTrue(engine.backtest_params[keys.backtest_start_date] is None)
        self.assertTrue(engine.backtest_params[keys.backtest_end_date] is None)

        longonly_params = {
            keys.lo_ticker: ['SGX_NK', 'LIFFE_FTI']
        }
        engine = adagio.Engine(backtest_start_date='2018-01-31',
                               backtest_end_date='2018-03-30')
        engine.add(adagio.LongOnly(**longonly_params))
        engine.backtest()
        self.assertEqual(engine.backtest_params[keys.backtest_start_date],
                         datetime(2018, 1, 31))
        self.assertEqual(engine.backtest_params[keys.backtest_end_date],
                         datetime(2018, 3, 30))

        lo = engine[0]
        self.assertEqual(lo[0].backtest_params[keys.backtest_start_date],
                         datetime(2018, 1, 31))
        self.assertEqual(lo[0].backtest_params[keys.backtest_end_date],
                         datetime(2018, 3, 30))
        self.assertEqual(lo[1].backtest_params[keys.backtest_start_date],
                         datetime(2018, 1, 31))
        self.assertEqual(lo[1].backtest_params[keys.backtest_end_date],
                         datetime(2018, 3, 30))

        c00 = lo[0].contracts[0]  # SGX/NKH2018
        self.assertEqual(c00[keys.start_date], None)
        self.assertEqual(c00[keys.end_date], datetime(2018, 3, 1))
        self.assertEqual(c00[keys.backtest_start_date], datetime(2018, 1, 31))
        self.assertEqual(c00[keys.backtest_end_date], datetime(2018, 3, 30))

    def test_spliced(self):
        engine_params = {
            keys.backtest_start_date: '1996-01-2',
            keys.backtest_end_date: '2000-12-29',
        }

        longonly_params = {
            keys.lo_ticker: 'CME_ES',
        }

        engine = adagio.Engine(**engine_params)
        engine.add(adagio.LongOnly(**longonly_params))
        engine.backtest()

        contracts = engine[0][0].contracts
        final_position = engine.get_final_positions()
        net_return = engine.get_final_net_returns()
        self.assertEqual(final_position.index[0],
                         datetime(1996, 1, 2))
        self.assertEqual(net_return.index[0],
                         datetime(1996, 1, 2))

        self.assertEqual(final_position.index[-1],
                         datetime(2000, 12, 29))
        self.assertEqual(net_return.index[-1],
                         datetime(2000, 12, 29))
        self.assertEqual(contracts[0].name, 'CME/SPH1996')
        self.assertEqual(contracts[-1].name, 'CME/ESH2001')

    def test_1st_futures(self):
        engine_params = {
            keys.backtest_start_date: '2017-01-03',
            keys.backtest_end_date: '2017-12-29',
        }

        longonly_params = {
            keys.lo_ticker: 'ICE_RF',
        }

        engine = adagio.Engine(**engine_params)
        engine.add(adagio.LongOnly(**longonly_params))
        engine.backtest()

        contracts = engine[0][0].contracts
        final_position = engine.get_final_positions()
        net_return = engine.get_final_net_returns()
        self.assertEqual(final_position.index[0],
                         datetime(2017, 1, 3))
        self.assertEqual(net_return.index[0],
                         datetime(2017, 1, 3))

        self.assertEqual(final_position.index[-1],
                         datetime(2017, 12, 29))
        self.assertEqual(net_return.index[-1],
                         datetime(2017, 12, 29))
        self.assertEqual(contracts[0].name, 'ICE/RFH2017')
        self.assertEqual(contracts[-1].name, 'ICE/RFH2018')

    def test_2nd_futures(self):
        engine_params = {
            keys.backtest_start_date: '2017-01-03',
            keys.backtest_end_date: '2017-12-29',
        }

        longonly_params = {
            keys.lo_ticker: 'ICE_RF',
            keys.nth_contract: 2,
        }

        engine = adagio.Engine(**engine_params)
        engine.add(adagio.LongOnly(**longonly_params))
        engine.backtest()

        contracts = engine[0][0].contracts
        final_position = engine.get_final_positions()
        net_return = engine.get_final_net_returns()
        self.assertEqual(final_position.index[0],
                         datetime(2017, 1, 3))
        self.assertEqual(net_return.index[0],
                         datetime(2017, 1, 3))

        self.assertEqual(final_position.index[-1],
                         datetime(2017, 12, 29))
        self.assertEqual(net_return.index[-1],
                         datetime(2017, 12, 29))
        self.assertEqual(contracts[0].name, 'ICE/RFM2017')
        self.assertEqual(contracts[-1].name, 'ICE/RFM2018')

    def test_symbol(self):
        engine_params = {
            keys.backtest_start_date: '2017-01-03',
            keys.backtest_end_date: '2017-12-29',
        }

        longonly_params = {
            keys.lo_ticker: 'ICE_RF',
            keys.nth_contract: 2,
        }

        engine = adagio.Engine(**engine_params)
        engine.add(adagio.LongOnly(**longonly_params))
        engine.backtest()
        symbol1 = engine.symbol

        engine_params = {
            keys.backtest_start_date: '2016-01-03',
            keys.backtest_end_date: '2017-12-29',
        }

        longonly_params = {
            keys.lo_ticker: 'ICE_RF',
            keys.nth_contract: 2,
        }

        engine = adagio.Engine(**engine_params)
        engine.add(adagio.LongOnly(**longonly_params))
        engine.backtest()
        symbol2 = engine.symbol

        self.assertEqual(symbol1, symbol2)


class TestMultipleEngine(unittest.TestCase):
    def setUp(self):
        longonly_params = {
            keys.lo_ticker: ['SGX_NK', 'LIFFE_FTI'],
        }
        lo_vol_scale_params = {
            keys.vs_chg_rule: '+Wed-1bd+1bd',
            keys.vs_target_vol: 0.1,
            keys.vs_method_params: {
                keys.vs_method: keys.vs_rolling,
                keys.vs_window: 63,
            }
        }
        signal_params = {
            keys.signal_method_params: {
                keys.signal_method: keys.signal_trend_ma_xover,
                keys.signal_windows: [[8, 24], [16, 48], [32, 96]],
            },
            keys.signal_chg_rule: '+Wed-1bd+1bd',
            keys.signal_to_position: keys.linear,
            keys.position_cap: 1.0,
            keys.position_floor: -1.0
        }
        portfolio_params = {
            keys.weighting: keys.equal_weight,
            keys.port_weight_chg_rule: '+Wed-1bd+1bd',
        }
        portfolio_vol_scale_params = {
            keys.vs_chg_rule: '+Wed-1bd+1bd',
            keys.vs_target_vol: 0.1,
            keys.vs_method_params: {
                keys.vs_method: keys.vs_rolling,
                keys.vs_window: 63,
            }
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

        self.assertTrue(isinstance(self.engine[0][0][0][0], LongOnlyQuandlFutures))
        self.assertTrue(isinstance(self.engine[0][0][0][1], LongOnlyQuandlFutures))
        self.assertTrue(isinstance(self.engine[0][0][1][0],
                                   adagio.VolatilityScaling))
        self.assertTrue(isinstance(self.engine[0][0][1][1],
                                   adagio.VolatilityScaling))
        self.assertTrue(isinstance(self.engine[0][0][2][0], adagio.Signal))
        self.assertTrue(isinstance(self.engine[0][0][2][1], adagio.Signal))

        self.assertTrue(isinstance(self.engine[0][1][0][0], LongOnlyQuandlFutures))
        self.assertTrue(isinstance(self.engine[0][1][0][1], LongOnlyQuandlFutures))
        self.assertTrue(isinstance(self.engine[0][1][1][0],
                                   adagio.VolatilityScaling))
        self.assertTrue(isinstance(self.engine[0][1][1][1],
                                   adagio.VolatilityScaling))
        self.assertTrue(isinstance(self.engine[0][1][2][0], adagio.Signal))
        self.assertTrue(isinstance(self.engine[0][1][2][1], adagio.Signal))

        position = self.engine[0][0][0][0].contracts[0].position
        self.assertEqual(position.columns[0], 'base')
        self.assertEqual(position.columns[1], 'volatility_scaling')
        self.assertEqual(position.columns[2], 'signal_trend_ma_xover')
        self.assertEqual(position.columns[3], 'portfolio')
        self.assertEqual(position.columns[4], 'portfolio_volatility_scaling')

        engine1_ret = self.engine[0][0].get_final_gross_returns().sum()
        engine2_ret = self.engine[0][1].get_final_gross_returns().sum()
        self.assertAlmostEqual(engine1_ret, engine2_ret)
        self.assertAlmostEqual(self.engine.get_final_gross_returns().sum(),
                               engine1_ret + engine2_ret)
