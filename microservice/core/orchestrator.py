import requests

from collections import defaultdict

from microservice import settings


class Orchestrator:
    # An instance of a MS *is* a resource, so refer to it as a uri.
    services = defaultdict(lambda: ['http://127.0.0.1:5000/microservice.development.functions.echo_as_dict'])
    # Is actually itself a MS

    @classmethod
    def service_uri(cls, service):
        return cls.services[service][0]

    @classmethod
    def discover(cls, func):
        if settings.deployment_type == settings.DeploymentType.ZERO:
            ms_function = func

        else:
            # Find the uri that represents the requested function hosted remotely.
            uri = Orchestrator.service_uri(func)

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

        return ms_function


def make_restful(uri, *args, **kwargs):
    # uses requests...
    return ""  # < func to call >


def serialise_function(func):
    return str(func)
