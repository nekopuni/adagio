import unittest
import pandas as pd

import adagio
from adagio.utils import keys


class TestScaling(unittest.TestCase):
    def test_vs_rolling(self):
        lo_vol_scale_params = {
            keys.vs_chg_rule: '+Wed-1bd+1bd',
            keys.vs_target_vol: 0.1,
            keys.vs_method_params: {
                keys.vs_method: keys.vs_rolling,
                keys.vs_window: 63,
            }
        }

        engine = adagio.Engine()
        engine.add(adagio.LongOnly(lo_ticker='CME_ES'))
        engine.add(adagio.VolatilityScaling(name='vs_pre_signal',
                                            **lo_vol_scale_params))
        engine.backtest()
        self.assertTrue(isinstance(engine.get_final_net_returns(),
                                   pd.Series))

    def test_vs_ewm(self):
        lo_vol_scale_params = {
            keys.vs_chg_rule: '+Wed-1bd+1bd',
            keys.vs_target_vol: 0.1,
            keys.vs_method_params: {
                keys.vs_method: keys.vs_ewm,
                keys.vs_ewm_halflife: 21,
            }
        }

        engine = adagio.Engine()
        engine.add(adagio.LongOnly(lo_ticker='CME_ES'))
        engine.add(adagio.VolatilityScaling(name='vs_pre_signal',
                                            **lo_vol_scale_params))
        engine.backtest()
        self.assertTrue(isinstance(engine.get_final_net_returns(),
                                   pd.Series))
