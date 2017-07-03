import pandas as pd

from .base import BaseStrategy
from ..utils import keys
from ..utils.logging import get_logger
from ..utils.const import ANNUAL_FACTOR
from ..utils.date import data_asfreq

logger = get_logger(name=__name__)


class BaseScaling(BaseStrategy):
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
        raw_returns = other.final_gross_returns
        self.position = (volatility_scale(raw_returns, self.backtest_params)
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

        raw_returns = pd.concat([i.final_gross_returns for i in others], axis=1)
        raw_returns = raw_returns.sum(axis=1)
        self.position = (volatility_scale(raw_returns, self.backtest_params)
                         .rename(self.name))


def volatility_scale(raw_returns, config):
    """ Calculate scaling factor to achieve target volatility

    :param raw_returns: dataframe containing return series
    :param config: dictionary with parameters for scaling
    :return: 
    """
    leverage = (raw_returns
                .rolling(config[keys.vs_window])
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
