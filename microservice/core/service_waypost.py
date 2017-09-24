import requests

from microservice.core import settings


class ServiceWaypost(dict):
    function_storage = {}

    local_services = []

    # TODO: obviously this needs to live elsewhere
    local_url = "http://127.0.0.1:5000"

    def register_local_service(self, service_name, func):
        print("Registering %s as local service:" % service_name)
        self.function_storage[service_name] = func
        self.local_services.append(service_name)

    def __getitem__(self, service_name):
        if service_name in self.function_storage.keys():
            print("Function %s location already known:" % service_name, self.function_storage[service_name])
            return self.function_storage[service_name]

        if settings.deployment_type == settings.DeploymentType.ZERO:
            func_name = service_name.split('.')[-1]
            mod_name = '.'.join(service_name.split('.')[:-1])
            mod = __import__(mod_name, globals(), locals(), [func_name], 0)
            func = getattr(mod, func_name)
            service = func
        elif settings.deployment_type == settings.DeploymentType.LOCAL:
            # Todo change this to "ask orchestrator where it is"
            uri = "%s/%s" % (self.local_url, service_name)

            print("Service is located at:", uri)

            # Wrapper to call the uri (i.e. remote function)
            def ms_function(*args, **kwargs):
                json_data = {
                    '_args': args,
                }
                json_data.update(kwargs)
                ret = requests.get(
                    uri,
                    json=json_data
                )
                print("Remote service returned json:", ret.json())
                # Functions can't return kwargs, so only return args.
                return ret.json()['_args']

            service = ms_function
        else:
            raise NotImplementedError

        self.function_storage[service_name] = service
        return service
