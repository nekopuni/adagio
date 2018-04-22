import pandas as pd
import numpy as np

from .base import BaseBacktestObject
from ..utils import keys
from ..utils.date import data_asfreq
from ..utils.logging import get_logger

logger = get_logger(name=__name__)


class Signal(BaseBacktestObject):
    def __init__(self, **backtest_params):
        backtest_params = self.init_params(**backtest_params)
        super(Signal, self).__init__(**backtest_params)
        self.position = None

    @classmethod
    def _compile(cls, **backtest_params):
        n_items = backtest_params.pop(keys.n_items)
        return [cls(**backtest_params) for _ in range(n_items)]

    @staticmethod
    def init_params(**backtest_params):
        """ Initialise parameters """
        backtest_params.setdefault(keys.position_floor, None)
        backtest_params.setdefault(keys.position_cap, None)

        signal_method_params = backtest_params[keys.signal_method_params]
        signal_windows = signal_method_params[keys.signal_windows]
        if isinstance(signal_windows, (int, float)):
            backtest_params[keys.signal_windows] = [signal_windows]
        return backtest_params

    @property
    def name(self):
        if keys.name in self.backtest_params:
            return self[keys.name]
        else:
            return self[keys.signal_method_params][keys.signal_method]

    def signal_to_position(self, signal):
        """ Convert signal to position """
        if self[keys.signal_to_position] == keys.linear:
            return signal.clip(lower=self[keys.position_floor],
                               upper=self[keys.position_cap])
        else:
            raise NotImplementedError()

    def backtest(self, other, *args, **kwargs):
        logger.info('Run layers: {}'.format(self))

        # signal calculation
        signal_method = self[keys.signal_method_params][keys.signal_method]
        signal_func = signal_method_map[signal_method]
        signal = (signal_func(other, self.backtest_params)
                  .rename(self.name))

        # convert signal to position
        self.position = self.signal_to_position(signal)


def signal_trend_ma_xover(other, config):
    """ Compute trend following signal using moving average cross-over.
    Multiple lookback windows can be applied to the signal calculation.

    :param raw_returns: dataframe containing return series
    :param config: dictionary with parameters for signals
    :return: 
    """
    raw_returns = other.get_final_net_returns()
    signal_method_params = config[keys.signal_method_params]
    signal = pd.concat([signal_trend_ma_xover_single(raw_returns, *w)
                        for w in signal_method_params[keys.signal_windows]],
                       axis=1)

    signal = (signal
              .mean(axis=1)
              .shift(2)  # trading lag
              .pipe(data_asfreq, config[keys.signal_chg_rule])
              .fillna(method='backfill'))
    return signal


def signal_trend_ma_xover_single(lo_return, st_window, lt_window):
    """ Compute trend following signal using moving average cross-over.
    
    :param lo_return: original return series
    :param st_window: integer for short-term window
    :param lt_window: integer for long-term window
    :return: 
    """
    if isinstance(lo_return, pd.Series):
        lo_return = pd.DataFrame(lo_return)
    assert len(lo_return.columns) == 1, 'lo_return should be uni-variate.'

    return lo_return.assign(
        ln_level=lambda df: df.add(1).cumprod().pipe(np.log)
    ).assign(
        st_trend=lambda df: df['ln_level'].ewm(halflife=st_window).mean(),
        lt_trend=lambda df: df['ln_level'].ewm(halflife=lt_window).mean()
    ).assign(
        raw_signal=lambda df: df['st_trend'].sub(df['lt_trend'])
    ).assign(
        signal=lambda df: (df['raw_signal']
                           .div(df['raw_signal'].ewm(halflife=252).std()))
    )[['signal']]


signal_method_map = {
    keys.signal_trend_ma_xover: signal_trend_ma_xover,
}
