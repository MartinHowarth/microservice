import requests

from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict


class Deployment:
    """
    This controls deploying a set of microservices.

    This is expected to be subclassed to provide the specifics for deploying onto different platforms, e.g.
        - subprocess (local only, no scale)
        - kubernetes (from env variables)
        - GCE / GKE
        - AWS
        - Azure
    """
    deployment_mode = None

    def __init__(self, service_names: List[str]):
        self.service_names = service_names
        self.services = {}  # type: Dict[str, object] # Values of an object representing the service in some way.

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.teardown()

    def setup(self):
        self.spawn_all_microservices()
        self.set_deployment_mode()

    def teardown(self):
        self.close_all_microservices()

    def spawn_all_microservices(self):
        pass

    def close_all_microservices(self):
        pass

    def uri_for_service(self, service_name):
        pass

    def send_request_to_all_services(self, uri_route, data=None, method=requests.get):
        results = dict()

        def make_request(_service_nane):
            response = method(
                self.uri_for_service(_service_nane) + uri_route,
                data=data,
            )
            results[_service_nane] = response

        with ThreadPoolExecutor() as executor:
            executor.map(make_request, self.services.keys())

        return results

    def set_deployment_mode(self):
        results = self.send_request_to_all_services(
            'deployment_mode',
            data={'deployment_mode': self.deployment_mode.value},
            method=requests.post)
        return results
