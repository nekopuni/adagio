from functools import reduce

import pandas as pd

from .layer import Layer
from .longonly import LongOnly
from ..utils import keys
from ..utils.array import merge_params
from ..utils.hash import to_hash
from ..utils.logging import get_logger

logger = get_logger(name=__name__)


class Engine(object):
    def __init__(self, **backtest_params):
        backtest_params = self.init_params(**backtest_params)
        self.backtest_params = backtest_params
        self.layers = []
        self.is_compiled = False

    def __repr__(self):
        layers = '\n\t'.join([str(i) for i in self.layers])
        return '{}(\n\t{}\n)'.format(self.__class__.__name__, layers)

    def __iter__(self):
        for layer in self.layers:
            yield layer

    def __len__(self):
        return len(self.layers)

    def __getitem__(self, item):
        return self.layers[item]

    @staticmethod
    def init_params(**backtest_params):
        """ Initialise parameters """
        backtest_params.setdefault(keys.name, 'engine')
        backtest_params.setdefault(keys.backtest_ccy, 'USD')
        return backtest_params

    @property
    def name(self):
        return self.backtest_params[keys.name]

    @property
    def symbol(self):
        """ Symbol used for MongoDB """
        return to_hash(self.all_params)

    @property
    def all_params(self):
        """ Merge backtest params in all layers """
        params = [item.backtest_params for layer in self for item in layer]
        params.append(self.backtest_params)
        all_params = reduce((lambda x, y: merge_params(x, y)), params)
        all_params[keys.name] = self.name
        return all_params

    def get_final_gross_returns(self):
        return (self.get_sub_gross_returns().sum(axis=1)
                .rename('final_gross_returns ({})'.format(self.name)))

    def get_final_net_returns(self):
        return (self.get_sub_net_returns().sum(axis=1)
                .rename('final_net_returns ({})'.format(self.name)))

    def get_sub_gross_returns(self):
        """ Return strategy gross sub-returns. If the first layer consists of 
        LongOnly, this returns each futures gross strategy returns.
        If the first layer is Engine, then this returns each Engine's 
        gross performance """
        return pd.concat([item.get_final_gross_returns() for item in self[0]], axis=1)

    def get_sub_net_returns(self):
        """ Return strategy net sub-returns. If the first layer consists of 
        LongOnly, this returns each futures net strategy returns.
        If the first layer is Engine, then this returns each Engine's 
        net performance """
        return pd.concat([item.get_final_net_returns() for item in self[0]], axis=1)

    def get_final_positions(self):
        """ Return strategy positions. This will be used if the first layer of 
        Engine consists of Engine instance(s) """
        return self.get_sub_positions()

    def get_sub_positions(self):
        """ Return strategy positions. If the first layer consists of 
        LongOnly, this returns each futures aggregated positions.
        If the first layer is Engine, then this returns each Engine's 
        positions """
        return pd.concat([item.get_final_positions() for item in self[0]], axis=1)

    def get_long_only_names(self):
        """ Return a list of LongOnly names """
        lo_list = []
        if all([isinstance(item, LongOnly) for item in self[0]]):
            for lo in self[0]:
                lo_list.append(lo.name)
        elif all([isinstance(item, Engine) for item in self[0]]):
            for engine in self[0]:
                lo_list = lo_list + engine.get_long_only_names()
        else:
            raise TypeError('Unknown the first layer type. Got {}'
                            .format(self[0]))
        return lo_list

    def add(self, other):
        """ Append an element to the layer """
        layer = Layer(other)
        self.layers.append(layer)

    def cascade(self, func_name, others=None):
        """ Look for a layer which has the specified function and run it """
        for layer in self:
            if all([hasattr(i, self.cascade.__name__) for i in layer]):
                #  in case layer consists of Engine
                for item in layer:
                    item.cascade(func_name, others=others)
                break

            else:
                try:
                    layer.run(func_name, others=others)
                    break
                except AttributeError:
                    pass

    def compile(self):
        """ Creates LongOnly objects etc according to the input parameters
        This must be called before calling backtest function
        """
        if not all([isinstance(item, (LongOnly, Engine)) for item in self[0]]):
            raise TypeError('The first layer must be composed of either only '
                            'LongOnly or Engine objects.')

        if not self.is_compiled:
            for layer_idx, layer in enumerate(self):
                try:
                    # if layer consists of Engine
                    # TODO check if layer is Engine instance?
                    layer.run("compile")
                except AttributeError:
                    if layer_idx > 0:
                        # Pass the number of objects in the previous layer
                        n_items = len(self[layer_idx - 1])
                        layer[0].backtest_params[keys.n_items] = n_items

                    layer.items = layer[0]._compile(**layer[0].backtest_params)

            self.cascade('set_return_currency',
                         others=[self.backtest_params[keys.backtest_ccy]])
            self.is_compiled = True

    def backtest(self):
        """ Run the layers by calling their functions in order """

        self.compile()
        root_layer = self[0]

        for layer_idx, layer in enumerate(self):
            if layer_idx == 0:
                # set up the first layer (usually LongOnly)
                layer.run('backtest')

            else:
                layer.run('backtest', others=root_layer)
                self.cascade('propagate_position', others=layer)

        logger.info('Backtest completed')
