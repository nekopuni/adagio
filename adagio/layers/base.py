class BaseBacktestObject(object):
    def __init__(self, **backtest_params):
        self._backtest_params = backtest_params

    def __getitem__(self, item):
        return self.backtest_params[item]

    def __setitem__(self, key, value):
        self.backtest_params[key] = value

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.backtest_params)

    @property
    def backtest_params(self):
        return self._backtest_params

    def backtest(self, *args, **kwargs):
        raise NotImplementedError()
