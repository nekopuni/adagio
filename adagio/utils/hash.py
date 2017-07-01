import hashlib
import json


def to_hash(obj):
    b = json.dumps(obj, sort_keys=True).encode()
    return hashlib.sha1(b).hexdigest()
