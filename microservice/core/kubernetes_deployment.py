from microservice.core import kube, settings
from microservice.core.deployment import Deployment


class KubernetesDeployment(Deployment):
    deployment_mode = settings.DeploymentMode.KUBERNETES

    def uri_for_service(self, service_name):
        return kube.uri_for_service(service_name)
