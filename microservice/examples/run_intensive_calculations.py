from microservice.core.service_waypost import init_service_waypost

from microservice.examples.intensive_calculators import (intensive_calculation_1, intensive_calculation_2,
                                                         intensive_calculation_3)


if __name__ == "__main__":
    init_service_waypost()

    for i in range(30):
        print("Intensive calculation 1x100000 says:", intensive_calculation_1(100000))
        # 3 calls into 2
        # Expectation is that, at this difficulty (at least on my PC) the usage of microservice intensive_calculation_2
        # nears 0% idle - so the orchestrator should scale it up.
        # Because 3 calls into 2, it will then start load balancing between the old and new instances
        # If you just run 2 directly from here, then we don't load balancer because this dumb client doesn't know how
        # to receive service updates.
        print("Intensive calculation 3x1000000 says:", intensive_calculation_3(1000000))
