from microservice.core.orchestrator import Orchestrator
from microservice import settings


def microservice(func):
    """
    Decorator that replaces the function with the restful call to make.
    """
    print(settings.this_service)
    print(func.__name__)
    if func.__name__ == settings.this_service:
        print("This function is being served locally")
        return func
    print("Decorating %s as microservice." % func)
    micro_function = Orchestrator.discover(func)
    print("Decorated as %s." % micro_function)
    return micro_function
