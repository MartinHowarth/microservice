import sys

import requests

from microservice import settings


class ServiceWaypost(dict):
    function_storage = {}

    # TODO: obviously this needs to live elsewhere
    local_url = "http://127.0.0.1:5000"

    def __getitem__(self, func):
        if func in self.function_storage.keys():
            print("Function %s location already known:" % func)
            return self.function_storage[func]

        if settings.deployment_type == settings.DeploymentType.ZERO:
            service = func
        elif settings.deployment_type == settings.DeploymentType.LOCAL:
            full_func_name = "%s.%s" % (sys.modules[func.__module__].__name__, func.__name__)
            uri = "%s/%s" % (self.local_url, full_func_name)

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

        self.function_storage[func] = service
        return service
