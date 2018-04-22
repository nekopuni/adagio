from functools import wraps
import re
from .const import QUANDL_FULL_TICKER_MATCH


def check_quandl_ticker(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not bool(re.match(QUANDL_FULL_TICKER_MATCH, args[0])):
            raise ValueError("{} is not a valid ticker.".format(args[0]))
        ret = func(*args, **kwargs)

        return ret

    return wrapper
