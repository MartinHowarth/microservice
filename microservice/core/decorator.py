import logging
import sys

from collections import namedtuple

from microservice.core import settings, communication, utils

logger = logging.getLogger(__name__)


MicroserviceDefinition = namedtuple("MicroserviceDefinition", ["name", "exposed"])


def microservice(method=None, exposed=False):
    """
    Decorator that declares a function as a microservice.
    This handles both calling out to a remote microservice, and being called as a microservice.

    Example usage:
      @microservice
      @microservice(exposed=True)

    :param function method: The function to turn into a microservice.
    :param bool exposed: Whether to expose this microservice outside of the microservice cluster.
    """
    def decorator(func):
        if sys.modules[func.__module__].__name__ == '__main__':
            # __main__ isn't static, so we can't ever allow a microservice to be defined in __main__ as other
            # microservices won't be able to locate it reliably.
            raise NotImplementedError("Can't have @microservice(s) defined in __main__.")

        service_name = utils.service_name_from_func(func)
        logger.debug("Function being decorated is: {full_service_name}", extra={'full_service_name': service_name})

        # When first importing any microservice decorated functions, record the name of the service so that we can
        # autodetect which services need to be created.
        settings.all_microservices.append(
            MicroserviceDefinition(service_name, exposed)
        )

        def runtime_discovery(*args, __message=None, **kwargs):
            # If this is called using args and kwargs, then this is being called to trigger a remote call
            # If this is called using __message, then this has been called as part of dealing with an actor message
            logger.debug(
                "Decorator for {service_name} received call: {arguments}, {keyword_arguments}, {calling_message}",
                extra={
                    'service_name': service_name,
                    'arguments': args,
                    'keyword_arguments': kwargs,
                    'calling_message': __message,
                })

            # If there is no message, then we must be calling into this function from an interface.
            # If there is a message, then this function is being called as a microservice.
            if __message is not None:
                args = __message.args
                kwargs = __message.kwargs

            if (settings.deployment_mode == settings.DeploymentMode.ZERO or
                    service_name == settings.ServiceWaypost.local_service):
                logger.info("{service_name} is being served locally.", extra={'service_name': service_name})
                return func(*args, **kwargs)

            logger.info("{service_name} is being served remotely.", extra={'service_name': service_name})
            # If we've already made the call to calculate this function, return that
            if (settings.communication_mode == settings.CommunicationMode.ACTOR and
                    settings.current_message() is not None):
                result_key = communication.create_result_key(service_name, args, kwargs)
                if result_key in settings.current_message().results.keys():
                    result = settings.current_message().get_result(service_name, args, kwargs)
                    logger.info("Call to that function already carried out - returning previous result: {result}",
                                extra={'result': result})
                    return result

            logger.info("Result has not been previously calculated.")
            if settings.communication_mode == settings.CommunicationMode.SYN:
                logger.debug("CommunicationMode is synchronous: calculating result synchronously.")
                ret_func = synchronous_function(service_name)
                return ret_func(*args, **kwargs)
            elif settings.communication_mode == settings.CommunicationMode.ACTOR:
                # Otherwise, make a call to another actor to carry it out and stop processing.
                logger.debug("CommunicationMode is asynchronous, sending request to another actor to fulfil request.")
                if settings.current_message() is not None:
                    communication.construct_and_send_call_to_service(
                        service_name,
                        settings.current_message(),
                        *args,
                        **kwargs
                    )
                    raise communication.ServiceCallPerformed(service_name)
                else:
                    # If there isn't an inbound microservice then we are making a call to a microservice from a
                    # non-microservice.
                    logger.info("Making call from interface, sending request, then waiting for async response back.")
                    return handle_interface_call(service_name, *args, **kwargs)

            raise ValueError("Invalid communication_mode")
        return runtime_discovery

    # Handle whether this decorator was called with arguments or not.
    if method is not None:
        # This decorator was called without arguments: i.e. `@microservice`
        # so we need to carry out the decoration, and return the new function
        return decorator(method)

    # Otherwise, this decorator was called with arguments: i.e. `@microservice(keyword=value)`
    # so we need to construct the decorator based on those arguments, and return that.
    return decorator


def handle_interface_call(service_name, *args, **kwargs):
    new_message = communication.Message()

    result_key = communication.create_result_key(service_name, args, kwargs)
    settings.set_interface_request(new_message.request_id, result_key)

    logger.debug("Sending interface call to {service_name}", extra={'service_name': service_name})
    communication.construct_and_send_call_to_service(
        service_name,
        new_message,
        *args,
        **kwargs
    )

    logger.debug("Waiting for response for request_id: {request_id}", extra={'request_id': new_message.request_id})

    def answer_is_ready():
        return new_message.request_id in settings.interface_results.keys()

    try:
        utils.wait_for(answer_is_ready)
        logger.debug("Got response to request_id: {request_id}", extra={'request_id': new_message.request_id})
        result = settings.interface_results[new_message.request_id]
    finally:
        if new_message.request_id in settings.interface_results.keys():
            del settings.interface_results[new_message.request_id]

    if isinstance(result, Exception):
        logger.exception(result)
        raise result
    return result


def synchronous_function(service_name):
    if settings.deployment_mode == settings.DeploymentMode.ZERO:
        logger.info("Deployment mode is ZERO, so calculating result locally")
        return utils.func_from_service_name(service_name)
        # func_name = service_name.split('.')[-1]
        # mod_name = '.'.join(service_name.split('.')[:-1])
        # mod = __import__(mod_name, globals(), locals(), [func_name], 0)
        # func = getattr(mod, func_name)
        # return func
    else:
        # Wrapper to call the uri (i.e. remote function)
        def ms_function(*args, **kwargs):
            logger.info("Sending synchronous request to service: {remote_service_name}", extra={
                'remote_service_name': service_name
            })
            result = communication.construct_and_send_call_to_service(
                service_name,
                settings.current_message(),
                *args,
                **kwargs
            )
            logger.info("Got synchronous result: {result}", extra={'result': result})
            return result
        return ms_function
