from microservice.core.orchestrator import Orchestrator
from microservice.core.service_waypost import init_service_waypost
from microservice.core import settings

from microservice.examples.echo import echo_as_dict2, echo_as_dict, echo_as_dict3


if __name__ == "__main__":
    init_service_waypost()
    settings.ServiceWaypost.orchestrator_uri = Orchestrator.uri

    # print("Echo as dict says:", echo_as_dict2(1, 2, 3, apple=5, banana="cabbage"))
    # print("Echo as dict says:", echo_as_dict(4, 5, 6, apple=5, banana="cabbage"))
    # print("Echo as dict says:", echo_as_dict(4, 5, 6, apple=5, banana="cabbage"))
    print("Echo as dict says:", echo_as_dict3(4, 5, 6, apple=5, banana="cabbage"))
