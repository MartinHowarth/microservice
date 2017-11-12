"""
Sample microservice to provide long-term slow-access storage.
Intent is that production/performance testing environments should use an existing open source database that actually has
features.
"""

from collections import defaultdict
from enum import Enum

from microservice.core.decorator import microservice


class DBSignals(Enum):
    PUT = "put"
    GET = "get"


SimpleKeyValueDatabase = defaultdict(lambda: None)


@microservice
def _db_wrapper(signal, key, value=None):
    if signal == DBSignals.PUT:
        SimpleKeyValueDatabase[key] = value
        retval = True
    elif signal == DBSignals.GET:
        retval = SimpleKeyValueDatabase[key]
    else:
        raise ValueError("Unrecognised DB signal received: %s" % signal)
    return retval


def put(key, value):
    return _db_wrapper(DBSignals.PUT, key=key, value=value)


def get(key):
    return _db_wrapper(DBSignals.GET, key=key)
