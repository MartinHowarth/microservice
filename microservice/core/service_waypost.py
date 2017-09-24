import enum

import requests


class DeploymentType(enum.Enum):
    ZERO = "ZERO"
    LOCAL = "LOCAL"
    DOCKER = "DOCKER"


class _ServiceWaypost:
    # For now, only a single orchestrator is supported.
    # If this is None, then we *are* the orchestrator.
    orchestrator_uri = 1

    deployment_type = DeploymentType.LOCAL

    service_locations = {}

    local_services = []

    # TODO: obviously this needs to live elsewhere
    local_url = "http://127.0.0.1:5000"

    def locate(self, service_name):
        if service_name in self.service_locations.keys():
            print("Function %s location already known:" % service_name, self.service_locations[service_name])
            return self.service_locations[service_name]

        if self.deployment_type == DeploymentType.ZERO:
            func_name = service_name.split('.')[-1]
            mod_name = '.'.join(service_name.split('.')[:-1])
            mod = __import__(mod_name, globals(), locals(), [func_name], 0)
            func = getattr(mod, func_name)
            service = func
        elif self.deployment_type == DeploymentType.LOCAL:
            if self.orchestrator_uri is not None:
                service_uri = self.locate_from_orchestrator(service_name)

                print("Service is located at:", service_uri)

                # Wrapper to call the uri (i.e. remote function)
                def ms_function(*args, **kwargs):
                    json_data = {
                        '_args': args,
                    }
                    json_data.update(kwargs)
                    ret = requests.get(
                        service_uri,
                        json=json_data
                    )
                    print("Remote service returned json:", ret.json())
                    # Functions can't return kwargs, so only return args.
                    return ret.json()['_args']

                service = ms_function
            else:
                raise RuntimeError("`orchestrator_uri` must be set before trying to discover services.")
        else:
            raise NotImplementedError

        self.service_locations[service_name] = service
        return service

    def locate_from_orchestrator(self, service_name):
        uri = "%s/%s" % (self.local_url, service_name)
        return uri

    def register_local_service(self, service_name, func):
        print("Registering %s as local service:" % service_name)
        self.service_locations[service_name] = func
        self.local_services.append(service_name)


ServiceWaypost = _ServiceWaypost()
