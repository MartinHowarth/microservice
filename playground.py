import requests
from time import sleep

from microservice.core.subprocess_cluster import SubprocessMicroserviceCluster

# Import all the definitions of microservices that we want to use
from microservice.tests import microservices_for_testing


microservices = [
    'microservice.tests.microservices_for_testing.echo_as_dict',
    'microservice.tests.microservices_for_testing.echo_as_dict2',
    'microservice.tests.microservices_for_testing.echo_as_dict3',
    'microservice.tests.microservices_for_testing.echo_as_dict4',
    'microservice.tests.microservices_for_testing.echo_as_dict5',
    'microservice.tests.microservices_for_testing.exception_raiser',
]

# with SubprocessMicroserviceCluster(microservices) as depl:
with SubprocessMicroserviceCluster() as depl:
    print(depl.all_microservices_are_alive())

    resp = requests.get(depl.uri_for_service('microservice.tests.microservices_for_testing.exception_raiser') + 'echo')
    print(resp.text)

    print([resp.text for resp in depl.send_request_to_all_services('deployment_mode').values()])
    print([resp.text for resp in depl.send_request_to_all_services('deployment_manager_uri').values()])

    sleep(10)
