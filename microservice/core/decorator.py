import sys

from microservice.core.orchestrator import Orchestrator
from microservice import settings


def microservice(func):
    """
    Decorator that replaces the function with the restful call to make.
    """
    def runtime_discovery(*args, **kwargs):
        print(settings.local_services)
        print(func.__name__)
        print(sys.modules[func.__module__].__name__)
        full_func_name = "%s.%s" % (sys.modules[func.__module__].__name__, func.__name__)
        if full_func_name in settings.local_services:
            print("This function is being served locally")
            ret_func = func
        else:
            print("Decorating %s as microservice." % func)
            ret_func = Orchestrator().discover(func)
            print("Decorated as %s." % ret_func)
        return ret_func(*args, **kwargs)
    return runtime_discovery
