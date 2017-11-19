from microservice.core import kube, settings
from microservice.core.communication import send_to_uri


class _ServiceWaypost:
    local_uri = None

    service_functions = dict()

    local_services = []

    running = False

    def start(self, **kwargs):
        self.running = True

    def locate(self, service_name):
        """
        Locate the microservices that provide the service specified by `service_name`.

        If the service has been previously used then the local cache of services is returned.
        If the service is not known, then the orchestrator is queried to find the locations.

        :param str service_name: The name of the service to locate.
        :return function: The function to call to send a request to the given service.
        """
        if service_name in self.service_functions.keys():
            print("Function for service {0} already created.".format(service_name))
            return self.service_functions[service_name]

        if settings.deployment_type == settings.DeploymentType.ZERO:
            func_name = service_name.split('.')[-1]
            mod_name = '.'.join(service_name.split('.')[:-1])
            mod = __import__(mod_name, globals(), locals(), [func_name], 0)
            func = getattr(mod, func_name)
            self.register_local_service(service_name, func)
        else:
            kube_name = kube.sanitise_name(service_name)
            service_uri = 'http://{kube_name}.{namespace}/'.format(
                kube_name=kube_name,
                namespace=settings.kube_namespace,
            )
            print("Service uri defined as: {}".format(service_uri))
            self.add_service_provider(service_name, service_uri)

        # Now that we've located the service, call back to this function to return it.
        return self.locate(service_name)

    def add_service_provider(self, service_name, service_uri):
        """
        Learn about a particular instance of a service.

        This creates the wrapper function for how to contact this instance later.

        :param str service_name: Name of the service for which an instance is being added.
        :param str service_uri: The URI of the specific instance being learned about
        """
        print("Service %s is provided by:" % service_name, service_uri)

        # Wrapper to call the uri (i.e. remote function)
        def ms_function(*args, **kwargs):
            result = send_to_uri(service_uri, *args, **kwargs)
            return result

        self.service_functions[service_name] = ms_function

    def register_local_service(self, service_name, func):
        """
        Register a service of given name to be a local service.
        This means that when trying to locate this service we won't query the orchestrator and we'll just call the
        function.

        :param str service_name: Name of the service to register as locally provided.
        :param function func: The actual local function to register.
        """
        print("Registering %s as local service." % service_name)
        self.service_functions[service_name] = func
        self.local_services.append(service_name)


def init_service_waypost(**kwargs):
    settings.ServiceWaypost = _ServiceWaypost()
    settings.ServiceWaypost.start(**kwargs)
