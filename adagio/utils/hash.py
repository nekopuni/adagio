from datetime import datetime
import hashlib
import json


def to_hash(obj):
    if isinstance(obj, datetime):
        # datetime is not hashable in which case it's converted into
        # unix timestamp
        obj = obj.strftime('%s')

    b = json.dumps(obj, sort_keys=True).encode()
    return hashlib.sha1(b).hexdigest()
