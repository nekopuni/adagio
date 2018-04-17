import re
from .decorators import check_quandl_ticker
from .const import FutureContractMonth


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
    contract_year = year(ticket)
    contract_month = futures_contract_month(ticket)
    contract_month = str(FutureContractMonth[contract_month].value).zfill(2)
    return int('{}{}'.format(contract_year, contract_month))
