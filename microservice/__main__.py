import argparse

from microservice.core import service_host


def start_service():
    parser = argparse.ArgumentParser()
    parser.add_argument("local_services", help="Comma-separated list of functions to provide as services.")
    args = parser.parse_args()
    services = args.local_services.split(',')
    print("This instance is providing the following services:")
    for service in services:
        print("\t", service)
    service_host.initialise_microservice(services)


if __name__ == "__main__":
    start_service()
