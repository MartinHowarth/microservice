import sys

from microservice.core import settings


def microservice(func):
    """
    Decorator that replaces the function with the restful call to make.
    """
    def runtime_discovery(*args, **kwargs):
        service_name = "%s.%s" % (sys.modules[func.__module__].__name__, func.__name__)
        print("Function being discovered is: {}".format(service_name))
        if (service_name in settings.ServiceWaypost.local_services or
                settings.deployment_type == settings.DeploymentType.ZERO):
            print("{} is being served locally.".format(service_name))
            ret_func = func
        else:
            print("{} is being served remotely.".format(service_name))
            ret_func = settings.ServiceWaypost.locate(service_name)
        return ret_func(*args, **kwargs)
    return runtime_discovery
