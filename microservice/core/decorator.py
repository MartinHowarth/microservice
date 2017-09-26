import sys

from requests.exceptions import ConnectionError

from microservice.core.service_waypost import ServiceWaypost, DeploymentType


def microservice(func):
    """
    Decorator that replaces the function with the restful call to make.
    """
    def runtime_discovery(*args, **kwargs):
        full_func_name = "%s.%s" % (sys.modules[func.__module__].__name__, func.__name__)
        print("Function being discovered is:", full_func_name)
        if full_func_name in ServiceWaypost.local_services or ServiceWaypost.deployment_type == DeploymentType.ZERO:
            print("This function is being served locally")
            ret_func = func
        else:
            print("Decorating %s as microservice." % func)
            ret_func = robust_service_call(full_func_name)
            print("Decorated as %s." % ret_func)
        return ret_func(*args, **kwargs)
    return runtime_discovery


def robust_service_call(service_name):
    """
    This causes this MS to think all instances of a service are down if a single one fails, and
    triggers a request to the orchestrator for a new set of references to the downed service.

    :param service_name:
    :return:
    """
    def robust_call(*args, **kwargs):
        service_uris = ServiceWaypost.locate(service_name)
        if ServiceWaypost.deployment_type == DeploymentType.ZERO:
            return ServiceWaypost.service_functions[service_uris[0]]

        service_uri = next(service_uris)
        service_function = ServiceWaypost.service_functions[service_uri]
        try:
            result = service_function(*args, **kwargs)
        except ConnectionError:
            # The service failed, so retire all local knowledge of it.
            ServiceWaypost.retire_service(service_name)

            # Re-locate the service, and then try and use it.
            service_uri = next(ServiceWaypost.locate(service_name))
            service_function = ServiceWaypost.service_functions[service_uri]
            result = service_function(*args, **kwargs)
        return result
    return robust_call
