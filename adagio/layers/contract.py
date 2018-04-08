from functools import partial
from datetime import datetime

import pandas as pd
import numpy as np
import quandl
from arctic.exceptions import NoDataFoundException

from .base import BaseBacktestObject
from ..utils import keys
from ..utils.config import AdagioConfig
from ..utils.const import (FutureContractMonth, Denominator, PriceSkipDates,
                           ReturnSkipDates, FuturesInfo, RETURN_KEY_PRIORITY)
from ..utils.date import date_shift
from ..utils.logging import get_logger
from ..utils.mongo import get_library
from ..utils.quandl import futures_contract_name, futures_contract_month, year

logger = get_logger(name=__name__)


class QuandlGeneric(BaseBacktestObject):
    def __init__(self, **backtest_params):
        super(QuandlGeneric, self).__init__(**backtest_params)


class GenericInstrument(BaseBacktestObject):
    def __init__(self, **backtest_params):
        super(GenericInstrument, self).__init__(**backtest_params)


class QuandlFutures(BaseBacktestObject):
    def __init__(self, **backtest_params):
        super(QuandlFutures, self).__init__(**backtest_params)
        self.data = None
        self.roll_date = None
        self.position = None
        self.is_expired = False

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__,
                               self[keys.quandl_ticker])

    @property
    def name(self):
        """ Return quandl ticker """
        return self[keys.quandl_ticker]

    @property
    def contract_name(self):
        """ Return contract name such as ES for S&P500 mini futures """
        return futures_contract_name(self[keys.quandl_ticker])

    @property
    def contract_month_code(self):
        """ Return month string representing the delivery month """
        return futures_contract_month(self[keys.quandl_ticker])

    @property
    def contract_month(self):
        """ Return delivery month """
        return FutureContractMonth[self.contract_month_code].value

    @property
    def contract_month_dt(self):
        """ Return the beginning of the month of delivery """
        return datetime(self.year, self.contract_month, 1).date()

    @property
    def year(self):
        """ Return delivery year """
        return year(self[keys.quandl_ticker])

    @property
    def price_for_return(self):
        """ Return a series for returns """
        return self.data[self.get_return_key()]

    def get_final_positions(self):
        """ Return final position (adjusted by signals etc.) 
        Trading lags are already applied so that the final return can be
        calculated by final_position * returns.
        """
        return self.position.prod(axis=1).rename('final_position')

    def get_final_gross_returns(self):
        """ Return final gross returns for its contract using final_positions 
        Any slippage is not deducted.
        """
        return ((self.calc_return() * self.get_final_positions())
                .rename('final_gross_returns'))

    def get_final_net_returns(self):
        """ Return final net returns for its contract using final_positions 
        
        Cost = tick size * slippage * trade amount / price_t
        trade amount is proportional to the trading size and is at least 1.0
        every time we trade.
        """
        # trade_amount = 1 if there is a transaction
        final_positions = self.get_final_positions()
        trade_amount = (final_positions.diff()
                        .shift(-1)  # trading lag is already added to positions
                        .fillna(0.0)
                        .abs())

        # initial entry if the position is held from start
        start_date = self.data.index[0]
        trade_amount[start_date] = abs(final_positions[start_date])

        cost = (self.price_for_return.pow(-1)
                .replace([np.inf, -np.inf], np.nan)
                .fillna(method='pad')
                .mul(self[keys.tick_size] * self[keys.slippage])
                .mul(trade_amount))
        return ((self.get_final_gross_returns() - cost)
                .rename('final_net_returns'))

    def get_final_returns(self, is_gross=True):
        if is_gross:
            return self.get_final_gross_returns()
        else:
            return self.get_final_net_returns()

    def backtest(self, start_date, end_date, *args, **kwargs):
        """ Get data from Quandl and clean it. Positions are calculated
        according to start_date and end_date (both including).

        :param start_date: 
        :param end_date: 
        :return: 
        """
        logger.info('Run layers: {}'.format(self))

        # load data
        self.data = self.load_data()
        self.data = self.clean_data()
        self.roll_date = end_date

        # determine base positions based on the roll date
        logger.debug('Determining base positions')
        self.position = pd.DataFrame(0.0, columns=['base'],
                                     index=self.data.index)
        self.position.loc[slice(start_date, end_date), 'base'] = 1.0
        self[keys.start_date] = start_date
        self[keys.end_date] = end_date

    def check_if_expired(self, data):
        """ Check if the contract is expired """
        if data.index[-1] >= self.last_trade_date():
            # if data contains the last trade date
            self.is_expired = True
        else:
            today = datetime.today()
            if data.index[-1] < date_shift(today, '-1y'):
                # if data is very old the contract is assumed to be expired
                self.is_expired = True

    def load_from_quandl(self):
        """ Download data from quandl """
        logger.debug('Downloading data from Quandl')
        data = quandl.get(self[keys.quandl_ticker],
                          api_key=AdagioConfig.quandl_token)
        self.check_if_expired(data)
        return data

    def to_mongo(self, library, data):
        """ Save data to MongoDB """
        logger.debug('Pushing data to MongoDB')
        library.write(self[keys.quandl_ticker], data)

    def load_data(self):
        """ Load data either from Quandl directly or MongoDB stored locally """

        library = get_library(keys.quandl_contract)
        try:
            item = library.read(self[keys.quandl_ticker])
            data = item.data
            self.check_if_expired(data)

            if not self.is_expired or self[keys.force_download]:
                # re-download data. Quandl might have more recent data
                data = self.load_from_quandl()
                self.to_mongo(library, data)
            else:
                logger.debug('Load data from MongoDB')

        except NoDataFoundException:
            # if not found in MongoDB, then it tries to get data from Quandl
            data = self.load_from_quandl()
            self.to_mongo(library, data)

        return data

    def get_date(self, shift_string):
        """ Shift date from the delivery month-begin """
        return date_shift(self.contract_month_dt, shift_string)

    def last_trade_date(self):
        return self.get_date(self[keys.last_trade_date])

    def first_notice_date(self):
        if self[keys.first_notice_date] is None:
            raise ValueError('{} not found.'.format(keys.first_notice_date))
        return self.get_date(self[keys.first_notice_date])

    def get_roll_date(self, roll_rule):
        """ Return roll date
         
        If there is no first notice date, then the roll date is X-days before
        its last trade date
        If the contract has a setting for first notice date, then the roll date
        is min(X-days before last trade date, X-days before first notice date)
        """
        _roll_date = date_shift(self.last_trade_date(), roll_rule)
        if self[keys.first_notice_date] is None:
            return _roll_date
        else:
            _roll_date_notice = date_shift(self.first_notice_date(),
                                           roll_rule)

            if _roll_date_notice < _roll_date:
                return _roll_date_notice
            else:
                raise ValueError("First notice should be earlier than "
                                 "last trading day.")

    def clean_data(self):
        """ Clean erroneous dates """
        cleaned_data = self.data

        if self[keys.lo_ticker] in PriceSkipDates.__members__.keys():
            dates = PriceSkipDates[self[keys.lo_ticker]].value
            skip_dates = pd.DatetimeIndex(dates)
            to_nan = [t for t in skip_dates if t in cleaned_data.index]
            cleaned_data.loc[to_nan] = None
            cleaned_data = (cleaned_data
                            .fillna(method='pad')
                            .fillna(method='bfill'))

        # remove when all prices are zero or negative for some reason
        flgs = self.price_for_return > 0
        cleaned_data = (cleaned_data.where(flgs).fillna(method='pad')
                        .fillna(method='bfill'))

        if self[keys.lo_ticker] in __fut_clean_func__.keys():
            cleaned_data = __fut_clean_func__[self[keys.lo_ticker]](
                cleaned_data)
        return cleaned_data

    def get_return_key(self):
        """ Return a column name used to be used for calculating returns """
        for return_key in RETURN_KEY_PRIORITY:
            if return_key in self.data.keys():
                return return_key
        raise ValueError('No return key found. Data contains {}'
                         .format(self.data.keys()))

    def calc_return(self):
        """ Calculate returns and clean it if necessary """
        return_raw = self._calc_return_raw()

        if self[keys.lo_ticker] in [i.name for i in ReturnSkipDates]:
            fix_date = ReturnSkipDates[self[keys.lo_ticker]].value
            for d in fix_date:
                if d in return_raw.index:
                    return_raw[d] = 0.0

        return_raw = self.convert_return_ccy(return_raw)

        return return_raw

    def _calc_return_raw(self):
        """ Return raw returns according to the denominator.
        (Fully-collateralised returns)
        
        If denominator is not specified, returns are just percentage changes.
        Other denominators follow the market conventions and/or the data format.
        """
        if self[keys.denominator] is None:
            base_price = self._get_base_price()
        else:
            if self[keys.denominator] == Denominator.GOVT_FUT.value:
                base_price = self._get_base_price(100.0)
            elif self[keys.denominator] == Denominator.MM_FUT.value:
                base_price = self._get_base_price(100.0 * 0.25)
            else:
                raise ValueError("{} is not a valid denominator."
                                 .format(self[keys.denominator]))
        return self.price_for_return.diff().div(base_price.shift()).fillna(0)

    def _get_base_price(self, constant=None):
        """ Get base price series that will be used as a denominator
        for return calculation """
        if constant is not None:
            base_price = pd.Series(constant, index=self.position.index)
        else:
            final_position = self.get_final_positions()
            position_change = (final_position
                               .shift(-1)
                               .fillna(method='pad')
                               .diff()
                               .abs()
                               .pipe(np.sign))
            # initial position
            position_change = (position_change
                               .fillna(final_position.abs().pipe(np.sign)))

            base_price = (self.price_for_return
                          .where(position_change == 1)
                          .fillna(method='pad'))

        # base_return is later shifted by 1 period when multiplied by
        # price change
        return base_price

    def convert_return_ccy(self, returns):
        """ Convert returns series into the backtest currency 
        
        This calculation assumes that the position is fully-collateralised 
        and the initial collateral is fully fx-hedged. 
    
        :param returns: returns series measured in the contract currency 
        :return: 
        """

        if self[keys.contract_ccy] == self[keys.backtest_ccy]:
            return returns
        else:
            library = get_library(keys.fx_rates)
            symbols = library.list_symbols(regex=self[keys.contract_ccy])

            if len(symbols) > 1:
                raise ValueError('Multiple fx rates found')

            fx_rates = library.read(symbols[0])
            fx_rates = fx_rates.data

            if fx_rates.name == '{}/{}'.format(self[keys.contract_ccy],
                                               self[keys.backtest_ccy]):
                # use fx rates as is
                pass
            elif fx_rates.name == '{}/{}'.format(self[keys.backtest_ccy],
                                                 self[keys.contract_ccy]):
                fx_rates = fx_rates.pow(-1)

            fx_adj = (fx_rates
                      .reindex(returns.index)
                      .fillna(method='pad')
                      .pct_change()
                      .fillna(0)
                      .add(1.0)
                      )
            return (returns * fx_adj).rename(returns.name)


def _clean_jgb_prices(df):
    df[:'2018-01-18'] *= 0.1
    return df


__fut_clean_func__ = {
    FuturesInfo.SGX_JB.name: _clean_jgb_prices
}
