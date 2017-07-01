from adagio.utils.hash import to_hash


def traverse(o, tree_types=(list, tuple)):
    """ Generator to access all items in a potentially nested array """
    if isinstance(o, tree_types):
        for value in o:
            for subvalue in traverse(value, tree_types):
                yield subvalue
    else:
        yield o


def merge_params(params1, params2):
    """ Merge two parameter sets in dictionary """
    if all([key1 not in params2 for key1 in params1]):
        # if keys in params1 and params2 are mutually exclusive
        return {**params1, **params2}

    else:
        combined = dict()
        combined_key = list(set(list(params1.keys()) + list(params2.keys())))

        for key in combined_key:
            if key in params1 and key in params2:
                value1 = params1[key]
                value2 = params2[key]

                # combine values
                if is_2d_list(value1) and not is_2d_list(value2):
                    value = value1 + [value2]
                elif not is_2d_list(value1) and is_2d_list(value2):
                    value = [value1] + value2
                elif is_2d_list(value1) and is_2d_list(value2):
                    value = [value1, value2]
                elif is_flat_list(value1) and is_flat_list(value2):
                    value = [value1, value2]
                else:
                    value = to_flat_list(value1) + to_flat_list(value2)

                # simplify values
                if all([to_hash(i) == to_hash(value[0]) for i in value]):
                    value = value[0]

                combined[key] = value
            else:
                combined[key] = params1.get(key, params2.get(key))

        return combined


def is_flat_list(array):
    """ Check if an array is a 1d list """
    if not isinstance(array, list):
        return False
    return all([not isinstance(i, list) for i in array])


def is_2d_list(array):
    """ Check if an array is a list of lists """
    if not isinstance(array, list):
        return False
    return all([isinstance(i, list) for i in array])


def is_same_flat_list(array1, array2):
    """ Check if all elements in two arrays are the same """
    if len(array1) != len(array2):
        return False
    return all([item1 == item2 for item1, item2 in zip(array1, array2)])


def to_flat_list(array):
    """ Convert to a 1d list """
    if not isinstance(array, list):
        return [array]
    return [item for item in traverse(array)]
