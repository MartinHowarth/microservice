"""
Wrapper around a memcached instance that is intended to provide fast-access storage for the state of
microservice'd objects.

Future todo's include:
- actually use memcached (or similar solution that provides a fast KV store
- make this scale across multiple hosts
    - don't want to replicate everything because that's going to bottleneck on the smallest host
    - but need one memcached instance with all relevant data per host for fast access
    - some clever pinning of stateful microservices to particular hosts may be required.
"""

from collections import defaultdict
from enum import Enum

from microservice.core.decorator import microservice


class DBSignals(Enum):
    PUT = "put"
    GET = "get"


FakeMemcachedDatabase = defaultdict(lambda: None)


@microservice
def _db_wrapper(signal, key, value=None):
    if signal == DBSignals.PUT:
        FakeMemcachedDatabase[key] = value
        retval = True
    elif signal == DBSignals.GET:
        retval = FakeMemcachedDatabase[key]
    else:
        raise ValueError("Unrecognised DB signal received: %s" % signal)
    return retval


def put(key, value):
    return _db_wrapper(DBSignals.PUT, key=key, value=value)


def get(key):
    return _db_wrapper(DBSignals.GET, key=key)
