from microservice.core.settings import local_waypost
import sys


def microservice(func):
    """
    Decorator that replaces the function with the restful call to make.
    """
    def runtime_discovery(*args, **kwargs):
        full_func_name = "%s.%s" % (sys.modules[func.__module__].__name__, func.__name__)
        print("Function being discovered is:", full_func_name)
        if full_func_name in local_waypost.local_services:
            print("This function is being served locally")
            ret_func = func
        else:
            print("Decorating %s as microservice." % func)
            ret_func = local_waypost[full_func_name]
            print("Decorated as %s." % ret_func)
        return ret_func(*args, **kwargs)
    return runtime_discovery
