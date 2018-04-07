class Layer(object):
    def __init__(self, items):
        if isinstance(items, list):
            self.items = items
        else:
            self.items = [items]

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.items)

    def __iter__(self):
        for item in self.items:
            yield item

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def run(self, func_name, others=None):
        """ Run a function given by func_name in the layers
        
        :param func_name: string representing a function name to run
        :param others: other Layer object to apply
        :return: 
        """

        if others is None:
            for item in self:
                getattr(item, func_name)()
        else:
            if len(self) == len(others):
                for item, other in zip(self, others):
                    getattr(item, func_name)(other)

            elif len(self) == 1:
                getattr(self[0], func_name)(others)

            elif len(others) == 1:
                for item in self:
                    getattr(item, func_name)(others[0])

            else:
                raise ValueError('Lengths mismatch.\n'
                                 'Self = {} while others = {}'
                                 .format(len(self), len(others)))
