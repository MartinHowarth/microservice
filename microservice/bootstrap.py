from typing import List

from microservice.core import dockr, kube


def detect_all_services() -> List[kube.KubeMicroservice]:
    services = []
    services.append(
        kube.KubeMicroservice(
            'microservice.examples.hello_world.hello_world',
            exposed_port=80,
        )
    )

    exposed_ports = [serv.exposed_port for serv in services]
    if len(exposed_ports) != len(set(exposed_ports)):
        raise ValueError(
            "Every microservice must be exposed on a unique port."
            "Additional k8s ingress integration in this project is required to lift this restriction."
            "The exposed ports are: {}".format(exposed_ports)
        )

    return services


def main():
    all_services = detect_all_services()

    # Create all the required docker images
    dockr.build_all_images([service.raw_name for service in all_services])

    # Build up the k8s deployment
    kube.pycroservice_init()
    for service in all_services:
        service.deploy()


if __name__ == "__main__":
    main()
