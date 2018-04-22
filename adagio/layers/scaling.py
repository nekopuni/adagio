import pandas as pd

from .base import BaseBacktestObject
from .longonly import LongOnly
from ..utils import keys
from ..utils.logging import get_logger
from ..utils.const import ANNUAL_FACTOR
from ..utils.date import data_asfreq

logger = get_logger(name=__name__)


class BaseScaling(BaseBacktestObject):
    def __init__(self, **backtest_params):
        backtest_params = self.init_params(**backtest_params)
        super(BaseScaling, self).__init__(**backtest_params)
        self.position = None

    @classmethod
    def _compile(cls, **backtest_params):
        n_items = backtest_params.pop(keys.n_items)
        return [cls(**backtest_params) for _ in range(n_items)]

    @staticmethod
    def init_params(**backtest_params):
        """ Initialise parameters """
        backtest_params.setdefault(keys.vs_floor, None)
        backtest_params.setdefault(keys.vs_cap, None)
        return backtest_params

    def backtest(self, *args, **kwargs):
        raise NotImplementedError()


class VolatilityScaling(BaseScaling):
    @property
    def name(self):
        if keys.name in self.backtest_params:
            return self[keys.name]
        else:
            return 'volatility_scaling'

    def backtest(self, other, *args, **kwargs):
        """ Calculate volatility scaling. 'other' can be a list of LongOnly.

        :param other: object from which volatility scaling is computed
        :return: 
        """
        logger.info('Run layers: {}'.format(self))
        raw_returns = other.get_final_net_returns()
        vs_func = vs_method_map[self[keys.vs_method_params][keys.vs_method]]
        self.position = (vs_func(raw_returns, self.backtest_params)
                         .rename(self.name))


class PortVolatilityScaling(BaseScaling):
    @property
    def name(self):
        if keys.name in self.backtest_params:
            return self[keys.name]
        else:
            return 'portfolio_volatility_scaling'

    def backtest(self, others, *args, **kwargs):
        """ Calculate volatility scaling. 'other' can be a list of LongOnly.

        :param others: layer of objects from which volatility scaling is computed
        :return: 
        """
        logger.info('Run layers: {}'.format(self))
        if isinstance(others, LongOnly):
            # others only contains one LongOnly object
            others = [others]

        raw_returns = pd.concat([i.get_final_net_returns()
                                 for i in others], axis=1)
        raw_returns = raw_returns.sum(axis=1)
        vs_func = vs_method_map[self[keys.vs_method_params][keys.vs_method]]
        self.position = (vs_func(raw_returns, self.backtest_params)
                         .rename(self.name))


def volatility_scale_rolling(raw_returns, config):
    """ Calculate scaling factor to achieve target volatility

    :param raw_returns: dataframe containing return series
    :param config: dictionary with parameters for scaling
    :return: 
    """
    vs_window = config[keys.vs_method_params][keys.vs_window]
    leverage = (raw_returns
                .rolling(vs_window)
                .std()
                .mul(ANNUAL_FACTOR ** 0.5)
                .pow(-1.0)
                .mul(config[keys.vs_target_vol])
                .clip(lower=config[keys.vs_floor],
                      upper=config[keys.vs_cap])
                .shift(2)  # trading lag
                .pipe(data_asfreq, config[keys.vs_chg_rule])
                .fillna(method='backfill'))
    return leverage


def volatility_scale_exponential(raw_returns, config):
    """ Calculate scaling factor to achieve target volatility using
    exponentially weighted rolling standard deviation.

    :param raw_returns: dataframe containing return series
    :param config: dictionary with parameters for scaling
    :return:
    """
    vs_method_params = config[keys.vs_method_params]
    com = vs_method_params.get(keys.vs_ewm_com, None)
    span = vs_method_params.get(keys.vs_ewm_span, None)
    halflife = vs_method_params.get(keys.vs_ewm_halflife, None)
    alpha = vs_method_params.get(keys.vs_ewm_alpha, None)
    leverage = (raw_returns
                .ewm(com=com, span=span, halflife=halflife, alpha=alpha)
                .std()
                .mul(ANNUAL_FACTOR ** 0.5)
                .pow(-1.0)
                .mul(config[keys.vs_target_vol])
                .clip(lower=config[keys.vs_floor],
                      upper=config[keys.vs_cap])
                .shift(2)  # trading lag
                .pipe(data_asfreq, config[keys.vs_chg_rule])
                .fillna(method='backfill'))
    return leverage


vs_method_map = {
    keys.vs_rolling: volatility_scale_rolling,
    keys.vs_ewm: volatility_scale_exponential,
}