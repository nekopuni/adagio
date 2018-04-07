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

        signal_windows = backtest_params[keys.signal_windows]
        if isinstance(signal_windows, (int, float)):
            backtest_params[keys.signal_windows] = [signal_windows]
        return backtest_params

    @property
    def name(self):
        if keys.name in self.backtest_params:
            return self[keys.name]
        else:
            return self[keys.signal_type]

    def get_signal_func(self):
        if self[keys.signal_type] == keys.momentum:
            return self.momentum
        else:
            raise NotImplementedError()

    def momentum(self, other):
        raw_returns = other.get_final_net_returns()
        signal = (momentum(raw_returns, self.backtest_params)
                  .rename(self.name))

        return signal

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
        signal_func = self.get_signal_func()
        signal = signal_func(other)

        # convert signal to position
        self.position = self.signal_to_position(signal)


def momentum(raw_returns, config):
    """ Compute time-series momentum signal. Multiple lookback windows can be
    applied to the signal calculation.

    :param raw_returns: dataframe containing return series
    :param config: dictionary with parameters for signals
    :return: 
    """
    signal = pd.concat([momentum_single(raw_returns, *w)
                        for w in config[keys.signal_windows]], axis=1)

    signal = (signal
              .mean(axis=1)
              .shift(2)  # trading lag
              .pipe(data_asfreq, config[keys.signal_chg_rule])
              .fillna(method='backfill'))
    return signal


def momentum_single(lo_return, st_window, lt_window):
    """ Compute time-series momentum signal
    
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
