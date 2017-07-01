from .base import BaseStrategy
from ..utils.logging import get_logger
from ..utils import keys

logger = get_logger(name=__name__)


class Portfolio(BaseStrategy):
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
        return 'portfolio'

    def backtest(self, other, *args, **kwargs):
        logger.info('Run layers: {}'.format(self))

        if self[keys.weighting] == keys.equal_weight:
            self.position = 1.0 / len(other)
        else:
            raise NotImplementedError()
