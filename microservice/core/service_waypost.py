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

    deployment_type = DeploymentType.LOCAL

    service_locations = defaultdict(LocalLoadBalancer)

    local_services = []

    def locate(self, service_name):
        if service_name in self.service_locations.keys():
            print("Function %s location already known:" % service_name, self.service_locations[service_name])
            return next(self.service_locations[service_name])

        if self.deployment_type == DeploymentType.ZERO:
            func_name = service_name.split('.')[-1]
            mod_name = '.'.join(service_name.split('.')[:-1])
            mod = __import__(mod_name, globals(), locals(), [func_name], 0)
            func = getattr(mod, func_name)
            self.service_locations[service_name].append(func)
        elif self.deployment_type == DeploymentType.LOCAL:
            service_uris = self.locate_from_orchestrator(service_name)
            for uri in service_uris:
                self.add_service_location(service_name, uri)
        else:
            raise NotImplementedError

        return next(self.service_locations[service_name])

    def add_service_location(self, service_name, service_uri):
        print("Service %s is located at:" % service_name, service_uri)

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

        self.service_locations[service_name].append(ms_function)

    def register_local_service(self, service_name, func):
        print("Registering %s as local service:" % service_name)
        self.service_locations[service_name].append(func)
        self.local_services.append(service_name)

    def locate_from_orchestrator(self, service_name):
        return self.ask_orchestrator("locate_service", service_name)

    def ask_orchestrator(self, action, *args, **kwargs):
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
