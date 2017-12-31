import enum
import pickle
import requests
from time import sleep

from microservice.core.communication import Message, send_object_to_service
from microservice.core.subprocess_deployment import SubprocessDeployment


microservices = [
    'microservice.tests.microservices_for_testing.echo_as_dict',
    'microservice.tests.microservices_for_testing.echo_as_dict2',
    'microservice.tests.microservices_for_testing.echo_as_dict3',
    'microservice.tests.microservices_for_testing.echo_as_dict4',
    'microservice.tests.microservices_for_testing.echo_as_dict5',
    'microservice.tests.microservices_for_testing.exception_raiser',
]


with SubprocessDeployment(microservices) as depl:
    print(depl.all_microservices_are_alive())

    resp = requests.get(depl.uri_for_service('microservice.tests.microservices_for_testing.exception_raiser') + 'echo')
    print(resp.text)

    print([resp.text for resp in depl.send_request_to_all_services('deployment_mode').values()])
    print([resp.text for resp in depl.send_request_to_all_services('deployment_manager_uri').values()])

    sleep(10)


