import re

import pandas as pd
import numpy as np
from numpy import int64
from pandas.tseries.offsets import *

# copied from pandas.tseries.offset
__all__ = {
    'day': Day,
    'businessday': BusinessDay,
    'bday': BDay,
    'custombusinessday': CustomBusinessDay,
    'cday': CDay,
    'cbmonthend': CBMonthEnd,
    'cbmonthbegin': CBMonthBegin,
    'monthbegin': MonthBegin,
    'bmonthbegin': BMonthBegin,
    'monthend': MonthEnd,
    'bmonthend': BMonthEnd,
    'businesshour': BusinessHour,
    'custombusinesshour': CustomBusinessHour,
    'yearbegin': YearBegin,
    'byearbegin': BYearBegin,
    'yearend': YearEnd,
    'byearend': BYearEnd,
    'quarterbegin': QuarterBegin,
    'bquarterbegin': BQuarterBegin,
    'quarterend': QuarterEnd,
    'bquarterend': BQuarterEnd,
    # 'lastweekofmonth': LastWeekOfMonth,
    # 'fy5253quarter': FY5253Quarter,
    # 'fy5253': FY5253,
    'week': Week,
    'weekofmonth': WeekOfMonth,
    'easter': Easter,
    'hour': Hour,
    'minute': Minute,
    'second': Second,
    'milli': Milli,
    'micro': Micro,
    'nano': Nano,

    # some helpers
    'bd': BDay,
    'd': DateOffset,
    'w': DateOffset,
    'm': DateOffset,
    'y': DateOffset,
    'mon': Week,
    'tue': Week,
    'wed': Week,
    'thu': Week,
    'fri': Week,
    'sat': Week,
    'sun': Week,
    'h': Hour,
    'min': Minute,
    'sec': Second
}

_offset_kwds = {
    'd': ['days', 1],
    'w': ['weeks', 1],
    'm': ['months', 1],
    'y': ['years', 1],
    'mon': ['weekday', 0],
    'tue': ['weekday', 1],
    'wed': ['weekday', 2],
    'thu': ['weekday', 3],
    'fri': ['weekday', 4],
    'sat': ['weekday', 5],
    'sun': ['weekday', 6]
}


def date_shift(dtime, shift_string):
    """
    Apply shift_string to dtime (can be either datetime or DatetimeIndex)

    :param dtime: base datetime one wants to shift
    :param shift_string: string representing how one wants to shift the
    base datetime
    :return: shifted datetime
    """
    _parsed_list = parse_shift_string(shift_string)
    for _offset in _parsed_list:
        dtime += _offset[0] * _offset[1]
    return dtime


def parse_shift_string(shift_string):
    """
    Convert shift_string into the list of shift integer and offset class.

    :param shift_string: string representing how one wants to shift the
    base datetime
    :return:
    """
    _shift_list = re.findall("[-+]?\w+", shift_string)
    _parsed_list = []

    for _offset in _shift_list:
        # split into shift integer and offset class name
        _shift_num = re.match("(^[-+]?[0-9]*)", _offset).group(0)
        _shift_str = _offset.replace(_shift_num, "")
        _split = [_shift_num, _shift_str]

        if _split[0] == "+":
            n = 1
        elif _split[0] == "-":
            n = -1
        else:
            n = int(_split[0])
        name = assign_offset_class(_split[1].lower())
        _parsed_list.append([n, name])
    return _parsed_list


def assign_offset_class(offset_name):
    _class = __all__[offset_name]
    if offset_name in _offset_kwds.keys():
        _kwds = _offset_kwds[offset_name]
        return eval("_class({}={})".format(_kwds[0], _kwds[1]))
    else:
        return _class()


def data_asfreq(data, shift_string, fill_method="pad"):
    """ Change the data frequency based on shift_string while keeping 
    the original index of data
    
    :param data: pandas series or dataframe
    :param shift_string: string representing how one wants to shift the
    base datetime. Data specified by this string will be returned.
    :param fill_method: fill method to be used for non-specified data
    :return: 
    """
    flg = freq_flg(data, shift_string)
    return data.where(flg.values > 0).fillna(method=fill_method)


def freq_flg(data, shift_string):
    """ Create series which contains flag values on dates specified
    by shift_string. Internal function. """
    tmp = data.copy(True)
    tmp.index = date_shift(data.index, shift_string)

    flg = pd.Series(tmp.index.astype(int64),
                    index=data.index).diff().fillna(0).pipe(np.sign)
    return flg
