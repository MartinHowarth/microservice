import logging
import sys

from microservice.core import settings, communication

logger = logging.getLogger(__name__)


def microservice(func):
    """
    Decorator that replaces the function with the restful call to make.
    """
    def runtime_discovery(*args, __message=None, **kwargs):
        # If this is called using args and kwargs, then this is being called to trigger a remote call
        # If this is called using __message, then this has been called as part of dealing with an actor message
        logger.debug("Decorator received call: {arguments}, {keyword_arguments}, {calling_message}", extra={
            'arguments': args,
            'keyword_arguments': kwargs,
            'calling_message': __message,
        })

        service_name = "%s.%s" % (sys.modules[func.__module__].__name__, func.__name__)
        logger.debug("Function being decorated is: {full_service_name}", extra={'full_service_name': service_name})

        if __message is not None:
            args = __message.args
            kwargs = __message.kwargs

        if (settings.deployment_mode == settings.Mode.ZERO or
                service_name == settings.ServiceWaypost.local_service):
            logger.info("{service_name} is being served locally.", extra={'service_name': service_name})
            return func(*args, **kwargs)

        logger.info("{service_name} is being served remotely.", extra={'service_name': service_name})
        # If we've already made the call to calculate this function, return that
        if settings.deployment_mode == settings.Mode.ACTOR:
            if service_name in settings.current_message().results.keys():
                result = settings.current_message().results[service_name]
                logger.info("Call to that function already carried out - returning previous result: {result}",
                            extra={'result': result})
                return result

        logger.info("Result has not been previously calculated.")
        if settings.deployment_mode == settings.Mode.SYN:
            logger.debug("Mode is synchronous: calculating result synchronously.")
            ret_func = synchronous_function(service_name)
            return ret_func(*args, **kwargs)
        elif settings.deployment_mode == settings.Mode.ACTOR:
            # Otherwise, make a call to another actor to carry it out and stop processing.
            logger.debug("Mode is asynchronous, sending request to another actor to fulfil request.")
            communication.construct_and_send_call_to_service(
                service_name,
                settings.ServiceWaypost.local_service,
                settings.current_message(),
                *args,
                **kwargs
            )
            raise communication.ServiceCallPerformed(service_name)

        raise ValueError("Invalid deployment_mode")
    return runtime_discovery


def synchronous_function(service_name):
    if settings.deployment_mode == settings.Mode.ZERO:
        logger.info("Deployment mode is ZERO, so calculating result locally")
        func_name = service_name.split('.')[-1]
        mod_name = '.'.join(service_name.split('.')[:-1])
        mod = __import__(mod_name, globals(), locals(), [func_name], 0)
        func = getattr(mod, func_name)
        return func
    else:
        # Wrapper to call the uri (i.e. remote function)
        def ms_function(*args, **kwargs):
            logger.info("Sending synchronous request to service: {remote_service_name}", extra={
                'remote_service_name': service_name
            })
            result = communication.construct_and_send_call_to_service(
                service_name,
                settings.ServiceWaypost.local_service,
                settings.current_message(),
                *args,
                **kwargs
            )
            logger.info("Got synchronous result: {result}", extra={'result': result})
            return result
        return ms_function
