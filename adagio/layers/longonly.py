from copy import copy
from datetime import datetime

import pandas as pd
import quandl

from .base import BaseBacktestObject
from .contract import QuandlFutures
from ..utils import keys
from ..utils.const import FuturesInfo, DEFAULT_ROLL_RULE, FutureContractMonth
from ..utils.date import date_shift
from ..utils.dict import merge_dicts
from ..utils.logging import get_logger
from ..utils.quandl import next_fut_ticker, futures_contract_month, year

logger = get_logger(name=__name__)


class LongOnly(BaseBacktestObject):
    def __init__(self, **backtest_params):
        backtest_params = self.init_params(**backtest_params)
        super(LongOnly, self).__init__(**backtest_params)
        self.contracts = None

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self[keys.lo_ticker])

    @classmethod
    def _compile(cls, **backtest_params):
        lo_ticker = backtest_params.pop(keys.lo_ticker)
        if isinstance(lo_ticker, str):
            lo_ticker = [lo_ticker]

        objs = []
        for ticker in lo_ticker:
            params = copy(backtest_params)
            params[keys.lo_ticker] = ticker
            futures_info = FuturesInfo[ticker].value
            params = merge_dicts(params, futures_info._asdict())
            objs.append(cls(**params))
        return objs

    @staticmethod
    def init_params(**backtest_params):
        """ Initialise parameters """
        backtest_params.setdefault(keys.force_download, False)
        backtest_params.setdefault(keys.slippage, 0.0)
        backtest_params.setdefault(keys.price_source, keys.pcs_quandl_futures)
        return backtest_params

    @property
    def name(self):
        return self[keys.lo_ticker]

    @property
    def first_ticker(self):
        return self[keys.lo_ticker].replace('_', '/') + self[keys.start_from]

    def get_final_gross_returns(self):
        """ Return gross long-only return series """
        return (self.aggregate_contract_returns(is_gross=True)
                .rename('final_gross_returns ({})'.format(self.name)))

    def get_final_net_returns(self):
        """ Return net long-only return series """
        return (self.aggregate_contract_returns(is_gross=False)
                .rename('final_net_returns ({})'.format(self.name)))

    def get_final_positions(self):
        """ Return aggregated positions for long-only returns """
        return (pd.concat([c.get_final_positions()
                           for c in self.contracts], axis=1)
                .sum(axis=1)
                .rename('final_positions ({})'.format(self.name)))

    def aggregate_contract_returns(self, is_gross):
        """ Sum up returns for each contract

        :param is_gross: bool. If True this gives gross returns otherwise
        returns after subtracting transaction cost estimates.
        :return:
        """
        return (pd.concat([c.get_final_returns(is_gross=is_gross)
                           for c in self.contracts], axis=1)
                .sum(axis=1))

    def backtest(self, *args, **kwargs):
        logger.info('Run layers: {}'.format(self))
        self.contracts = self.get_contracts()

    def get_contracts(self):
        """ Returns contract objects based on price source """
        if self[keys.price_source] == keys.pcs_quandl_futures:
            ticker = self.first_ticker
            contracts = []
            start_date = None

            while True:
                try:
                    params = copy(self.backtest_params)
                    params[keys.quandl_ticker] = ticker  # individual

                    contract = QuandlFutures(**params)
                    end_date = contract.get_roll_date(DEFAULT_ROLL_RULE)

                    contract.backtest(start_date, end_date)
                    start_date = date_shift(end_date, '+1bd')
                    contracts.append(contract)

                except (quandl.NotFoundError, IndexError):
                    # if the requesting contract is far future
                    # Usually quandl throws NotFoundError, but sometimes it gets
                    # IndexError.
                    m = FutureContractMonth[futures_contract_month(ticker)]
                    tmp_last_dt = datetime(year(ticker), m.value, 1)
                    tmp_last_dt = date_shift(tmp_last_dt, "+MonthEnd")
                    if tmp_last_dt.date() > datetime.today().date():
                        break

                ticker = next_fut_ticker(ticker, self[keys.roll_schedule])
            self.contracts = contracts
        else:
            raise NotImplemented()

        return contracts

    def propagate_position(self, other):
        """ Propagate position to individual contract level """
        for contract in self.contracts:
            if isinstance(other.position, (pd.DataFrame, pd.Series)):
                other_position = other.position
            elif isinstance(other.position, float):
                other_position = pd.Series(other.position,
                                           name=other.name,
                                           index=contract.position.index)
            elif isinstance(other.position, dict):
                other_position = other.position[self.name]
                other_position = pd.Series(other_position,
                                           name=other.name,
                                           index=contract.position.index)
            else:
                raise NotImplementedError()

            contract.position = contract.position.join(other_position)

    def set_return_currency(self, currency):
        """ Propagate return currency to individual contract level """
        self[keys.backtest_ccy] = currency
