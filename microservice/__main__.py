import argparse

from microservice.core import service_host, orchestrator


def start_service():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local_services", help="Comma-separated list of functions to provide as services.")
    parser.add_argument("--orchestrator", help="Start as an orchestrator.", action="store_true")
    args = parser.parse_args()

    if args.orchestrator:
        orchestrator.initialise_orchestration()
    else:
        services = args.local_services.split(',')
        print("This instance is providing the following services:")
        for service in services:
            print("\t", service)
        service_host.initialise_microservice(services)


if __name__ == "__main__":
    start_service()
