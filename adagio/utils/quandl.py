import re
from .decorators import check_quandl_ticker
from .const import (FutureContractMonth, QUANDL_FULL_TICKER_MATCH,
                    QUANDL_GENERIC_TICKER_MATCH, QUANDL_TICKER_FORMAT)
from .mongo import get_library
from . import keys


@check_quandl_ticker
def exchange(ticker):
    """ Return exchange name such as 'CME' """
    return ticker.split('/')[0]


@check_quandl_ticker
def year(ticker):
    """ Return the expiry year such as 2017 in SPH2017 """
    ret = re.findall('[0-9]{4}', ticker)

    # TODO: issue might occur when ticker has more than 4 digits.
    if len(ret) != 1:
        raise ValueError('{} does not valid year information.'.format(ticker))
    return int(ret[0])


@check_quandl_ticker
def futures_contract_name(ticker):
    """ Return the contract name such as 'SP' """
    name = ticker.split('/')[1].split(str(year(ticker)))[0]
    return name[:-1]


@check_quandl_ticker
def futures_contract_month(ticker):
    """ Return the month identifier such as 'H' for March """
    name = ticker.split('/')[1].split(str(year(ticker)))[0]
    return name[-1]


@check_quandl_ticker
def next_fut_ticker(ticker, roll_schedule):
    """ Return the next nearest ticker according to the roll schedule """
    _exchange = exchange(ticker)
    _year = year(ticker)
    _name = futures_contract_name(ticker)
    _month = futures_contract_month(ticker)

    if _month not in roll_schedule:
        raise ValueError("Ticker and roll schedule don't match. "
                         "Ticker: {}, Roll schedule: {}"
                         .format(ticker, roll_schedule))

    _idx = roll_schedule.index(_month)
    if _idx == len(roll_schedule) - 1:
        return "{}/{}{}{}".format(_exchange, _name, roll_schedule[0], _year + 1)
    else:
        return "{}/{}{}{}".format(_exchange, _name, roll_schedule[_idx + 1],
                                  _year)


@check_quandl_ticker
def to_yyyymm(ticket):
    """ Convert a full Quandl ticker to yyyymm (delivery month).
    e.g., CME/ESH2000 -> 200003 """
    contract_year = year(ticket)
    contract_month = futures_contract_month(ticket)
    contract_month = str(FutureContractMonth[contract_month].value).zfill(2)
    return int('{}{}'.format(contract_year, contract_month))


def is_generic_futures_ticker(generic_ticker):
    """ Check if the given ticker is generic """
    if not bool(re.match(QUANDL_FULL_TICKER_MATCH, generic_ticker)):
        if bool(re.match(QUANDL_GENERIC_TICKER_MATCH, generic_ticker)):
            return True
    else:
        return False


def get_tickers_from_db(generic_ticker, start_yyyymm=None, end_yyyymm=None):
    """ Return a sorted list of individual tickers for the given generic
    Both start_yyyymm and end_yyyymm are inclusive

    :param generic_ticker: generic ticker such as CME/ES
    :param start_yyyymm: int, start date (YYYYMM)
    :param end_yyyymm: int, end date (YYYYMM)
    :return:
    """
    if not is_generic_futures_ticker(generic_ticker):
        raise ValueError('{} is not a generic Quandl ticker'
                         .format(generic_ticker))

    library = get_library(keys.quandl_contract)
    symbol_regex = QUANDL_TICKER_FORMAT.format(generic_ticker)
    all_tickers = library.list_symbols(regex=symbol_regex)
    all_tickers.sort(key=to_yyyymm)

    if start_yyyymm is not None:
        all_tickers = [i for i in all_tickers if to_yyyymm(i) >= start_yyyymm]
    if end_yyyymm is not None:
        all_tickers = [i for i in all_tickers if to_yyyymm(i) <= end_yyyymm]
    return all_tickers
