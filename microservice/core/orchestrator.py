import requests
import sys

from microservice import settings


class ServiceWaypost(dict):
    uri_storage = {}

    # TODO: obviously this needs to live elsewhere
    local_url = "http://127.0.0.1:5000"

    def __getitem__(self, func):
        if settings.deployment_type == settings.DeploymentType.ZERO:
            service = func
        elif settings.deployment_type == settings.DeploymentType.LOCAL:
            print(func.__name__)
            print(sys.modules[func.__module__].__name__)
            full_func_name = "%s.%s" % (sys.modules[func.__module__].__name__, func.__name__)
            print("Full func name:", full_func_name)
            uri = "%s/%s" % (self.local_url, full_func_name)

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
                print(ret)
                print(ret.status_code)
                print(ret.text)
                print(ret.json())
                # Functions can't return kwargs, so only return args.
                return ret.json()['_args']

            service = ms_function
        else:
            raise NotImplementedError

        return service


class Orchestrator:
    # An instance of a MS *is* a resource, so refer to it as a uri.
    # services = defaultdict(lambda: ['http://127.0.0.1:5000/microservice.development.functions.echo_as_dict'])
    # Is actually itself a MS
    service_waypost = ServiceWaypost()

    def discover(self, func):
        return self.service_waypost[func]
