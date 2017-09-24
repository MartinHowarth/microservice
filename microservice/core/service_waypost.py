import enum
import requests


class DeploymentType(enum.Enum):
    ZERO = "ZERO"
    LOCAL = "LOCAL"
    DOCKER = "DOCKER"


class _ServiceWaypost:
    # For now, only a single orchestrator is supported.
    # If this is None, then we *are* the orchestrator.
    # orchestrator_uri = None
    orchestrator_uri = "http://127.0.0.1:4999/orchestration"

    deployment_type = DeploymentType.LOCAL

    service_locations = {}

    local_services = []

    def locate(self, service_name):
        if service_name in self.service_locations.keys():
            print("Function %s location already known:" % service_name, self.service_locations[service_name])
            return self.service_locations[service_name]

        if self.deployment_type == DeploymentType.ZERO:
            func_name = service_name.split('.')[-1]
            mod_name = '.'.join(service_name.split('.')[:-1])
            mod = __import__(mod_name, globals(), locals(), [func_name], 0)
            func = getattr(mod, func_name)
            self.service_locations[service_name] = func
        elif self.deployment_type == DeploymentType.LOCAL:
            service_uri = self.locate_from_orchestrator(service_name)
            self.add_service_location(service_name, service_uri)
        else:
            raise NotImplementedError

        return self.service_locations[service_name]

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

        self.service_locations[service_name] = ms_function

    def register_local_service(self, service_name, func):
        print("Registering %s as local service:" % service_name)
        self.service_locations[service_name] = func
        self.local_services.append(service_name)

    def locate_from_orchestrator(self, service_name):
        if self.orchestrator_uri is None:
            # This only exists for testing.
            return "%s/%s" % ("http://127.0.0.1:5000", service_name)
        return self.ask_orchestrator("locate_service", service_name)
        # return self.locate_service(service_name)
        # json_data = {
        #     'action': 'locate_service',
        #     'service_name': service_name,
        # }
        # ret = requests.get(
        #     self.orchestrator_uri,
        #     json=json_data
        # )
        # return ret.json()['uri']

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
        return ret.json()['_args']


ServiceWaypost = _ServiceWaypost()
