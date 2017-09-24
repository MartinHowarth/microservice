from microservice.development.functions import echo_as_dict2, echo_as_dict, echo_as_dict3
from microservice.core.service_waypost import ServiceWaypost
from microservice.core.orchestrator import Orchestrator

if __name__ == "__main__":
    ServiceWaypost.orchestrator_uri = Orchestrator.uri

    print("Echo as dict says: %s" % echo_as_dict2(1, 2, 3, apple=5, banana="cabbage"))
    print("Echo as dict says: %s" % echo_as_dict(4, 5, 6, apple=5, banana="cabbage"))
    print("Echo as dict says: %s" % echo_as_dict(4, 5, 6, apple=5, banana="cabbage"))
    print("Echo as dict says: %s" % echo_as_dict3(4, 5, 6, apple=5, banana="cabbage"))
