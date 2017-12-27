import argparse
import json
import logging

from microservice.core.microservice_logging import configure_logging

logger = logging.getLogger(__name__)


def start_service():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", help="Name of service.")
    parser.add_argument("--host", help="IP address to host the service on.")
    parser.add_argument("--port", help="Port to host the service on.")
    parser.add_argument("--other_kwargs")
    args = parser.parse_args()

    if args.other_kwargs:
        other_kwargs = json.loads(args.other_kwargs)
    else:
        other_kwargs = {}

    configure_logging(args.service)

    logger.info("This instance is providing the following service: {service_name}",
                extra={'service_name': args.service})
    from microservice.core import service_host
    service_host.initialise_microservice(args.service, args.host, args.port, **other_kwargs)


if __name__ == "__main__":
    start_service()

    # TODO: IMPORTANT: before program termination, close the fluentd logging handler
    # But at the moment, we only close when crashing, so defer.
    # h.close()
