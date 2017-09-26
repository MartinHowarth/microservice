from microservice.core.service_waypost import ServiceWaypost
from microservice.core.orchestrator import Orchestrator

from microservice.examples.intensive_calculators import intensive_calculation_1, intensive_calculation_2


if __name__ == "__main__":
    ServiceWaypost.orchestrator_uri = Orchestrator.uri

    for i in range(30):
        print("Intensive calculation 1x100 says:", intensive_calculation_1(100000))
        print("Intensive calculation 2x1000 says:", intensive_calculation_2(1000000))
