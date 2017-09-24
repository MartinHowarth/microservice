import argparse

from microservice.core import service_host, orchestrator


def start_service():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local_services", help="Comma-separated list of functions to provide as services.")
    parser.add_argument("--orchestrator", help="Start as an orchestrator.", action="store_true")
    parser.add_argument("--host", help="IP address to host the service on.")
    parser.add_argument("--port", help="Port to host the service on.")
    args = parser.parse_args()

    if args.orchestrator:
        orchestrator.initialise_orchestration()
    else:
        services = args.local_services.split(',')
        print("This instance is providing the following services:")
        for service in services:
            print("\t", service)
        service_host.initialise_microservice(services, args.host, args.port)


if __name__ == "__main__":
    start_service()
