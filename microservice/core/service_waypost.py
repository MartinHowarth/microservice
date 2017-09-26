import enum
import requests

from collections import defaultdict

from microservice.core.load_balancer import LocalLoadBalancer


class DeploymentType(enum.Enum):
    ZERO = "ZERO"
    LOCAL = "LOCAL"
    DOCKER = "DOCKER"


class _ServiceWaypost:
    orchestrator_uri = None

    local_uri = None

    deployment_type = DeploymentType.LOCAL

    service_providers = defaultdict(LocalLoadBalancer)
    service_functions = dict()

    local_services = []

    def locate(self, service_name):
        if service_name in self.service_providers.keys() and len(self.service_providers[service_name]):
            print("Function %s provider already known:" % service_name, self.service_providers[service_name])
            return self.service_providers[service_name]
            # return self.service_functions[self.service_providers[service_name]]

        if self.deployment_type == DeploymentType.ZERO:
            func_name = service_name.split('.')[-1]
            mod_name = '.'.join(service_name.split('.')[:-1])
            mod = __import__(mod_name, globals(), locals(), [func_name], 0)
            func = getattr(mod, func_name)
            self.register_local_service(service_name, func)
        elif self.deployment_type == DeploymentType.LOCAL:
            service_uris = self.locate_from_orchestrator(service_name)
            for uri in service_uris:
                self.add_service_provider(service_name, uri)
        else:
            raise NotImplementedError

        # Now that we've located the service, call back to this function to return it.
        return self.locate(service_name)

    def retire_service(self, service_name):
        if service_name in self.service_providers.keys():
            uris = self.service_providers[service_name]
            for uri in uris:
                del self.service_functions[uri]
            del self.service_providers[service_name]

        self.send_to_orchestrator("report_service_failure",
                                  service_name)

    def remove_service_provider(self, service_name, service_uri):
        print("Service providers are:", self.service_providers[service_name])
        try:
            self.service_providers[service_name].remove(service_uri)
        except ValueError:
            pass

    def add_service_provider(self, service_name, service_uri):
        print("Service %s is provided by:" % service_name, service_uri)

        # Wrapper to call the uri (i.e. remote function)
        def ms_function(*args, **kwargs):
            json_data = {
                '_args': args,
                '_kwargs': kwargs,
            }
            ret = requests.get(
                service_uri,
                json=json_data
            )
            print("Remote service returned json:", ret.json())
            # Functions can't return kwargs, so only return args.
            return ret.json()['_args']

        self.service_providers[service_name].append(service_uri)
        self.service_functions[service_uri] = ms_function

    def register_local_service(self, service_name, func):
        print("Registering %s as local service:" % service_name)
        uri = "local%s" % func
        self.service_providers[service_name].append(uri)
        self.service_functions[uri] = func
        self.local_services.append(service_name)

    def locate_from_orchestrator(self, service_name):
        return self.send_to_orchestrator("locate_provider", service_name, self.local_uri)

    def send_to_orchestrator(self, action, *args, **kwargs):
        json_data = {
            'action': action,
            '_args': args,
            '_kwargs': kwargs
        }
        print("Asking orchestrator for:", json_data)
        ret = requests.get(
            self.orchestrator_uri,
            json=json_data
        )
        print("Received:", ret)
        return ret.json()['_args']


ServiceWaypost = _ServiceWaypost()
