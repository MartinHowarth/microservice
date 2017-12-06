import sys

from microservice.core import settings, communication


def microservice(func):
    """
    Decorator that replaces the function with the restful call to make.
    """
    def runtime_discovery(*args, __message=None, **kwargs):
        # If this is called using args and kwargs, then this is being called to trigger a remote call
        # If this is called using __message, then this has been called as part of dealing with an actor message
        service_name = "%s.%s" % (sys.modules[func.__module__].__name__, func.__name__)
        print("Function being discovered is: {}".format(service_name))

        if __message is not None:
            args = __message.args
            kwargs = __message.kwargs

        if (service_name == settings.ServiceWaypost.local_service or
                settings.deployment_type == settings.DeploymentType.ZERO):
            print("{} is being served locally.".format(service_name))
            return func(*args, **kwargs)

        print("{} is being served remotely.".format(service_name))
        # If we've already made the call to calculate this function, return that
        if settings.deployment_mode == settings.Mode.ACTOR:
            print("Call to that function already carried out - returning previous result.")
            if service_name in settings.ServiceWaypost.current_message.results.keys():
                return settings.ServiceWaypost.current_message.results[service_name]

        if settings.deployment_mode == settings.Mode.SYN:
            ret_func = discover_function(service_name)
            return ret_func(*args, **kwargs)
        elif settings.deployment_mode == settings.Mode.ACTOR:
            # Otherwise, make a call to another actor to carry it out and stop processing.
            communication.construct_and_send_call_to_service(
                service_name,
                settings.ServiceWaypost.local_service,
                settings.ServiceWaypost.current_message,
                *args,
                **kwargs
            )
            raise communication.ServiceCallPerformed("{}".format(service_name))

        raise ValueError("Invalid deployment_mode")
    return runtime_discovery


def discover_function(service_name):
    if settings.deployment_type == settings.DeploymentType.ZERO:
        func_name = service_name.split('.')[-1]
        mod_name = '.'.join(service_name.split('.')[:-1])
        mod = __import__(mod_name, globals(), locals(), [func_name], 0)
        func = getattr(mod, func_name)
        return func
    else:
        service_uri = communication.uri_from_service_name(service_name)
        print("Service uri defined as: {}".format(service_uri))

        # Wrapper to call the uri (i.e. remote function)
        def ms_function(*args, **kwargs):
            return communication.send_to_uri(__uri=service_uri, *args, **kwargs)
        return ms_function
