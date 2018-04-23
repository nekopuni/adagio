import pandas as pd

from .base import BaseBacktestObject
from .engine import Engine
from .longonly import LongOnly
from ..utils.date import data_asfreq
from ..utils.logging import get_logger
from ..utils import keys

logger = get_logger(name=__name__)


class Portfolio(BaseBacktestObject):
    """ Layer to bind strategies """

    def __init__(self, **backtest_params):
        super(Portfolio, self).__init__(**backtest_params)
        self.position = None

    @classmethod
    def _compile(cls, **backtest_params):
        backtest_params.pop(keys.n_items)
        return [cls(**backtest_params)]

    @property
    def name(self):
        if keys.name in self.backtest_params:
            return self[keys.name]
        else:
            return 'portfolio'

    def backtest(self, other, *args, **kwargs):
        logger.info('Run layers: {}'.format(self))

        if self[keys.weighting] == keys.equal_weight:
            if isinstance(other, LongOnly):
                # portfolio only contains one LongOnly object
                other = [other]
            # equally allocate across available instruments at that time
            ret = pd.concat([i.get_final_gross_returns() for i in other],
                            axis=1).fillna(method='pad')
            self.position = (ret.count(axis=1).pow(-1.0)
                             .pipe(data_asfreq, self[keys.port_weight_chg_rule])
                             .rename(self.name))

        elif isinstance(self[keys.weighting], list):
            self.position = dict()
            for item, weight in zip(other, self[keys.weighting]):
                if isinstance(item, LongOnly):
                    self.position[item.name] = weight
                elif isinstance(item, Engine):
                    lo_list = item.get_long_only_names()
                    for lo in lo_list:
                        self.position[lo] = weight
                else:
                    raise TypeError('Unexpected object is passed: {}'
                                    .format(item))

        else:
            raise NotImplementedError()
