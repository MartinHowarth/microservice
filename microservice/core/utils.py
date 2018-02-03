import logging
import sys
import time

logger = logging.getLogger(__name__)


def func_from_service_name(service_name: str) -> callable:
    """
    Work out the func that corresponds given `service_name`.

    :param str service_name: Service name to translate back into a function.
    :return function: Function represented by given service name.
    """
    func_name = service_name.split('.')[-1]
    mod_name = '.'.join(service_name.split('.')[:-1])
    mod = __import__(mod_name, globals(), locals(), [func_name], 0)
    func = getattr(mod, func_name)
    logger.debug("Dynamically found module is: {mod}", extra={'mod': mod})
    logger.debug("Dynamically found function is: {func}", extra={'func': func})
    return func


def service_name_from_func(func: callable) -> str:
    """
    Work out the name of the microservice that corresponds to `func`.

    :param function func: Function that is being turned into a microservice
    :return str: Microservice name.
    """
    module_name = sys.modules[func.__module__].__name__
    service_name = "%s.%s" % (module_name, func.__name__)
    return service_name


def wait_for(condition: callable, interval: float=0.01, timeout: int=60):
    timer = 0
    while not condition():
        time.sleep(interval)
        timer += interval
        if timer > timeout:
            raise TimeoutError("Timeout waiting for condition %s" % condition)
