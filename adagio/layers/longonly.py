import abc
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
from ..utils.quandl import (next_fut_ticker, futures_contract_month, year,
                            get_tickers_from_db, to_yyyymm)

logger = get_logger(name=__name__)


class LongOnly(BaseBacktestObject):
    _backtest_params = [keys.lo_ticker]

    def __init__(self, **backtest_params):
        backtest_params = self.init_params(**backtest_params)
        super(LongOnly, self).__init__(**backtest_params)
        self.contracts = None

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self[keys.lo_ticker])

    @staticmethod
    def _compile(**backtest_params):
        lo_ticker = backtest_params.pop(keys.lo_ticker)
        if isinstance(lo_ticker, str):
            lo_ticker = [lo_ticker]

        objs = []
        class_map = {
            keys.pcs_quandl_futures: LongOnlyQuandlFutures,
            keys.pcs_truefx: LongOnlyTrueFX,
        }
        class_constructor = class_map[backtest_params[keys.price_source]]
        for ticker in lo_ticker:
            params = copy(backtest_params)
            params[keys.lo_ticker] = ticker
            objs.append(class_constructor(**params))
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
        return (self.get_individual_positions()
                .sum(axis=1)
                .rename('final_positions ({})'.format(self.name)))

    def get_individual_positions(self, date_range=None):
        """ Return individual positions for each underlying contracts """
        positions = (pd.concat([c.get_final_positions().rename(c.name)
                                for c in self.contracts], axis=1))
        if date_range is not None:
            positions = positions.loc[date_range, :]

        return positions.dropna(how='all', axis=1)

    def aggregate_contract_returns(self, is_gross):
        """ Sum up returns for each contract

        :param is_gross: bool. If True this gives gross returns otherwise
        returns after subtracting transaction cost estimates.
        :return:
        """
        return (pd.concat([c.get_final_returns(is_gross=is_gross)
                           for c in self.contracts], axis=1)
                .sum(axis=1))

    @abc.abstractmethod
    def backtest(self, *args, **kwargs):
        """ Run backtest """

    @abc.abstractmethod
    def get_contracts(self):
        """ Collect contract information """

    @abc.abstractmethod
    def update_database(self):
        """ Update database if necessary for underlying contract objects """

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

    def set_backtest_start_date(self, backtest_start_date):
        self[keys.backtest_start_date] = backtest_start_date

    def set_backtest_end_date(self, backtest_end_date):
        self[keys.backtest_end_date] = backtest_end_date


class LongOnlyQuandlFutures(LongOnly):
    def __init__(self, **backtest_params):
        super(LongOnlyQuandlFutures, self).__init__(**backtest_params)

    def init_params(self, **backtest_params):
        ticker = backtest_params[keys.lo_ticker]
        # fixme lo_ticker must exist in FuturesInfo
        futures_info = FuturesInfo[ticker].value
        backtest_params = merge_dicts(backtest_params, futures_info._asdict())
        backtest_params.setdefault(keys.backtest_ccy,
                                   backtest_params[keys.contract_ccy])
        backtest_params.setdefault(keys.nth_contract, 1)
        backtest_params[keys.is_spliced] = ticker in _splice_func_map

        # common params for LongOnly
        backtest_params = super(LongOnlyQuandlFutures, self).init_params(**backtest_params)
        return backtest_params

    @property
    def first_ticker(self):
        return self[keys.lo_ticker].replace('_', '/') + self[keys.start_from]

    def backtest(self, *args, **kwargs):
        """ Run backtest """
        logger.info('Run layers: {}'.format(self))
        self.contracts = self.get_contracts()

    def get_individual_prices(self, date_range=None, keys=None):
        """ Return concatenated price data from all contracts

        :param keys: list of key names. If None price data to compute returns
        is retrieved.
        :return:
        """
        if keys is None:
            all_prices = pd.concat([i.price_for_return
                                    for i in self.contracts], axis=1)
        else:
            all_prices = pd.concat([i.data[keys]
                                    for i in self.contracts], axis=1)

        if date_range is not None:
            all_prices = all_prices.loc[date_range, :]

        all_prices.columns = [i.name for i in self.contracts]
        return all_prices.dropna(how='all', axis=1)

    def get_futures_curve(self, date):
        """ Return futures curve for a given date

        :param date: date on which the futures curve is observed
        :return:
        """
        return self.get_individual_prices(slice(date, date)).squeeze()

    def get_generic_volume(self):
        """ Return historical trading volume of contracts that are used for
        long-only performance """
        base_positions = pd.concat([i.position['base'].rename(i.name)
                                    for i in self.contracts], axis=1)

        if self.contracts[0].has_volume:
            key_name = self.contracts[0].get_volume_key()
            volume = pd.concat([i.data[key_name].rename(i.name)
                                for i in self.contracts], axis=1)
            return base_positions.mul(volume).sum(axis=1).rename(key_name)
        else:
            # return NaN if volume doesn't exist
            return pd.Series(index=base_positions.index)

    def get_contracts(self):
        """ Return a list of available futures contract objects """
        contracts = []
        start_date = None
        if self[keys.backtest_start_date] is not None:
            start_yyyymm = int(self[keys.backtest_start_date].strftime('%Y%m'))
        else:
            start_yyyymm = 190001

        if self[keys.is_spliced]:
            all_tickers = _splice_func_map[self[keys.lo_ticker]](
                start_yyyymm=start_yyyymm
            )
        else:
            all_tickers = get_tickers_from_db(self[keys.lo_ticker]
                                              .replace('_', '/'),
                                              start_yyyymm=start_yyyymm)

        for idx, ticker in enumerate(all_tickers):
            # all tickers are instantiated regardless of nth_contract as
            # old contracts might be used to get roll dates.
            params = copy(self.backtest_params)
            params[keys.quandl_ticker] = ticker  # individual
            contract = QuandlFutures(**params)
            contracts.append(contract)

            if idx >= self[keys.nth_contract] - 1:
                contract_for_roll = contracts[idx - self[keys.nth_contract]
                                              + 1]
                end_date = contract_for_roll.get_roll_date(DEFAULT_ROLL_RULE)
                contract.backtest(start_date, end_date)
                start_date = date_shift(end_date, '+1bd')

                # Trim position and data baed on backtest period
                contract._trim_data()
                if self[keys.backtest_end_date] is not None:
                    if start_date > self[keys.backtest_end_date]:
                        break

        # Remove contracts that are not used
        # For instance, if we want to use second contract,
        # the very first contract is not necessary for the backtest
        contracts = contracts[(self[keys.nth_contract] - 1):]

        # Remove ones that are completely trimmed
        contracts = [i for i in contracts if len(i.data) > 0]

        return contracts

    def update_database(self):
        """ Update database if necessary for underlying contract objects """
        ticker = self.first_ticker

        while True:
            try:
                params = copy(self.backtest_params)
                params[keys.quandl_ticker] = ticker  # individual
                logger.info('Checking if new data exists: {}'.format(ticker))

                contract = QuandlFutures(**params)
                contract.update_database()

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


class LongOnlyTrueFX(LongOnly):
    def __init__(self, **backtest_params):
        super(LongOnlyTrueFX, self).__init__(**backtest_params)


def _get_spliced_symbols(lo_tickers, ranges, start_yyyymm, end_yyyymm):
    """ Return a list of spliced tickers

    :param lo_tickers: list of lo_ticker
    :param ranges: list of list containing two yyyymm (both side including)
    :param start_yyyymm: int, start date (YYYYMM)
    :param end_yyyymm: int, end date (YYYYMM)
    :return:
    """
    if len(lo_tickers) != len(ranges):
        raise ValueError('Length mismatch. lo_tickers={}, ranges={}'
                         .format(lo_tickers, ranges))
    all_symbols = [get_tickers_from_db(i, start_yyyymm=start_yyyymm,
                                       end_yyyymm=end_yyyymm)
                   for i in lo_tickers]
    result = []
    for symbols, range in zip(all_symbols, ranges):
        result += [s for s in symbols if range[0] <= to_yyyymm(s) <= range[1]]
    return result


# wait for 1 year after the introduction of the new ticker before switching
# to allow it to have enough data.
def splice_es_and_sp(start_yyyymm=None, end_yyyymm=None):
    lo_tickers = ['CME/SP', 'CME/ES']
    ranges = [[0, 199811], [199812, 999912]]
    return _get_spliced_symbols(lo_tickers, ranges, start_yyyymm, end_yyyymm)


def splice_nq_and_nd(start_yyyymm=None, end_yyyymm=None):
    lo_tickers = ['CME/ND', 'CME/NQ']
    ranges = [[0, 200008], [200009, 999912]]
    return _get_spliced_symbols(lo_tickers, ranges, start_yyyymm, end_yyyymm)


def splice_ym_and_dj(start_yyyymm=None, end_yyyymm=None):
    lo_tickers = ['CME/DJ', 'CME/YM']
    ranges = [[0, 201302], [201303, 999912]]
    return _get_spliced_symbols(lo_tickers, ranges, start_yyyymm, end_yyyymm)


_splice_func_map = {
    FuturesInfo.CME_ES._name_: splice_es_and_sp,
    FuturesInfo.CME_NQ._name_: splice_nq_and_nd,
    FuturesInfo.CME_YM._name_: splice_ym_and_dj,
}
