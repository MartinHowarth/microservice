import threading
import time

from collections import defaultdict

from microservice.core import pubsub
from microservice.core import settings
from microservice.core.communication import send_to_mgmt_of_uri, send_to_uri
from microservice.core.health_checker import HealthChecker
from microservice.core.load_balancer import LocalLoadBalancer
from microservice.core.stethoscope import notify_stethoscope


class _ServiceWaypost:
    orchestrator_uri = None

    local_uri = None

    service_providers = defaultdict(LocalLoadBalancer)
    service_functions = dict()

    local_services = []

    running = False
    _disable_heartbeating = False
    _heartbeat = None
    heartbeat_interval = 1

    def start(self, disable_heartbeating=None, **kwargs):
        if disable_heartbeating is not None:
            self._disable_heartbeating = disable_heartbeating

        if not self._disable_heartbeating:
            self._heartbeat = threading.Thread(target=self.heartbeat)

        self.running = True

    def heartbeat(self):
        while self.running:
            time.sleep(self.heartbeat_interval)
            notify_stethoscope(self.local_uri, HealthChecker.heartbeat_info)

    def locate(self, service_name):
        """
        Locate the microservices that provide the service specified by `service_name`.

        If the service has been previously used then the local cache of services is returned.
        If the service is not known, then the orchestrator is queried to find the locations.

        :param str service_name: The name of the service to locate.
        :return LocalLoadBalancer: The list of uri's that provide the requested service. Wrapped up as a
            LocalLoadBalancer object for ease of use.
        """
        if service_name in self.service_providers.keys() and len(self.service_providers[service_name]):
            print("Function %s provider already known:" % service_name, self.service_providers[service_name])
            return self.service_providers[service_name]

        if settings.deployment_type == settings.DeploymentType.ZERO:
            func_name = service_name.split('.')[-1]
            mod_name = '.'.join(service_name.split('.')[:-1])
            mod = __import__(mod_name, globals(), locals(), [func_name], 0)
            func = getattr(mod, func_name)
            self.register_local_service(service_name, func)
        elif settings.deployment_type == settings.DeploymentType.LOCAL:
            service_uris = self.locate_from_orchestrator(service_name)
            for uri in service_uris:
                self.add_service_provider(service_name, uri)
        else:
            raise NotImplementedError

        # Now that we've located the service, call back to this function to return it.
        return self.locate(service_name)

    def retire_service(self, service_name):
        """
        Forget that a service exists. Remove all local knowledge of it.

        One use case is to trigger a re-request to the orchestrator for this service next time that it is used.

        :param str service_name: Name of the service to retire.
        """
        if service_name in self.service_providers.keys():
            uris = self.service_providers[service_name]
            for uri in uris:
                del self.service_functions[uri]
            del self.service_providers[service_name]

        self.send_to_orchestrator("report_service_failure", service_name)

    def remove_service_provider(self, service_name, service_uri):
        """
        Forget that a particular instance of a service exists.

        :param str service_name: Name of the service to forget.
        :param str service_uri: The URI of the specific instance to forget about.
        """
        print("Service providers are:", self.service_providers[service_name])
        try:
            self.service_providers[service_name].remove(service_uri)
        except ValueError:
            pass

    def add_service_provider(self, service_name, service_uri):
        """
        Learn about a particular instance of a service.

        This creates the wrapper function for how to contact this instance later.

        :param str service_name: Name of the service for which an instance is being added.
        :param str service_uri: The URI of the specific instance being learned about
        """
        print("Service %s is provided by:" % service_name, service_uri)
        # Subscribe to new service after defining it locally so we don't tight loop on subscribing
        # to the pubsub service.
        is_new_service = True if service_name not in self.service_providers else False

        # Wrapper to call the uri (i.e. remote function)
        def ms_function(*args, **kwargs):
            result = send_to_uri(service_uri, *args, **kwargs)
            return result

        # Don't add the service if we already know about it
        if service_uri not in self.service_providers[service_name]:
            self.service_providers[service_name].append(service_uri)
            self.service_functions[service_uri] = ms_function

        if is_new_service and self.local_uri:
            # Don't subscribe if local uri is None. Local uri is only none when we're running as a non-MS instance,
            # for instance, as a unit test.
            print("Subscribing to service:", service_name)
            pubsub.subscribe(service_name, self.local_uri)

    def register_local_service(self, service_name, func):
        """
        Register a service of given name to be a local service.
        This means that when trying to locate this service we won't query the orchestrator and we'll just call the
        function.

        :param str service_name: Name of the service to register as locally provided.
        :param function func: The actual local function to register.
        """
        print("Registering %s as local service:" % service_name)
        uri = "__local__.%s" % func
        self.service_providers[service_name].append(uri)
        self.service_functions[uri] = func
        self.local_services.append(service_name)

    def locate_from_orchestrator(self, service_name):
        """
        Ask the orchestrator for the locations (URIs) of microservices that serve the given `service_name`.

        :param str service_name: Name of the service to locate.
        :return list[str]: List of URI's.
        """
        return self.send_to_orchestrator("locate_provider", service_name, self.local_uri)

    def send_to_orchestrator(self, action, *args, **kwargs):
        """
        Helper function to send any request to the orchestrator.

        :param str action: Action to trigger on the orchestrator. See the `management_waypost` in orchestrator.py.
        :param args: Args to send with the request.
        :param kwargs: Kwargs to send with the request.
        :return: Whatever the orchestrator returns.
        """
        result = send_to_mgmt_of_uri(self.orchestrator_uri, *args, __action=action, **kwargs)
        return result

    def current_deployment_information(self):
        return {
            'service_providers': self.service_providers,
        }


def init_service_waypost(**kwargs):
    settings.ServiceWaypost = _ServiceWaypost()
    settings.ServiceWaypost.start(**kwargs)
