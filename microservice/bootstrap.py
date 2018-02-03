from typing import List

from microservice.core import dockr, kube, settings


def detect_all_services() -> List[kube.KubeMicroservice]:
    services = [
        kube.KubeMicroservice(
            'microservice.examples.hello_world.hello_world',
        ),
        kube.KubeMicroservice(
            'microservice.examples.hello_world.hello_other_world',
        ),
        kube.KubeMicroservice(
            'microservice.examples.intensive_calculators.intensive_calculator_fanout',
            exposed=True,
        ),
        kube.KubeMicroservice(
            'microservice.examples.intensive_calculators.intensive_calculation_1',
        ),
        kube.KubeMicroservice(
            'microservice.examples.intensive_calculators.intensive_calculation_2',
        ),
        kube.KubeMicroservice(
            'microservice.examples.intensive_calculators.intensive_calculation_3',
        ),
    ]

    exposed = [serv for serv in services if serv.exposed]
    if len(exposed) > 1:
        raise ValueError(
            "Only one microservice can be exposed."
            "Additional k8s ingress integration in this project is required to lift this restriction."
            "The exposed services are: {}".format(exposed)
        )

    return services


def main():
    # Create all the required docker images
    dockr.build_all_images([service.name for service in settings.all_microservices])

    k8s_services = [
        kube.KubeMicroservice(service.name, service.exposed)
        for service in settings.all_microservices
    ]

    # Build up the k8s deployment
    kube.pycroservice_init()
    for service in k8s_services:
        service.deploy()


if __name__ == "__main__":
    main()
