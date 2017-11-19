import argparse
import json

from microservice.core import settings


def start_service():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local_services", help="Comma-separated list of functions to provide as services.")
    parser.add_argument("--host", help="IP address to host the service on.")
    parser.add_argument("--port", help="Port to host the service on.")
    parser.add_argument("--other_kwargs")
    args = parser.parse_args()

    if args.other_kwargs:
        other_kwargs = json.loads(args.other_kwargs)
    else:
        other_kwargs = {}

    services = args.local_services.split(',')
    print("This instance is providing the following services:")
    for service in services:
        print("\t", service)
    from microservice.core import service_host
    service_host.initialise_microservice(services, args.host, args.port, **other_kwargs)


if __name__ == "__main__":
    start_service()
