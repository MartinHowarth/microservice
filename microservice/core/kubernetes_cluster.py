from microservice.core import kube, settings, dockr
from microservice.core.microservice_cluster import MicroserviceCluster


class KubernetesMicroserviceCluster(MicroserviceCluster):
    deployment_mode = settings.DeploymentMode.KUBERNETES

    def uri_for_service(self, service_name):
        return kube.uri_for_service(service_name)

    def spawn_all_microservices(self):
        # Create all the required docker images
        dockr.build_all_images([service.name for service in self.service_definitions])

        k8s_services = [
            kube.KubeMicroservice(service.name, service.exposed)
            for service in self.service_definitions
        ]

        # Build up the k8s deployment
        kube.pycroservice_init()
        for service in k8s_services:
            service.deploy()
