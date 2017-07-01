from functools import wraps


def check_quandl_ticker(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "/" not in args[0]:
            raise Exception("{} is not a valid ticker.".format(args[0]))
        ret = func(*args, **kwargs)

        return ret

    return wrapper
