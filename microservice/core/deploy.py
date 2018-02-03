from microservice.core import settings
from microservice.core.subprocess_cluster import SubprocessMicroserviceCluster
from microservice.core.kubernetes_cluster import KubernetesMicroserviceCluster


def create_deployment(*args, **kwargs):
    if settings.deployment_mode == settings.DeploymentMode.ZERO:
        return
    elif settings.deployment_mode == settings.DeploymentMode.SUBPROCESS:
        settings.ServiceWaypost.deployment = SubprocessMicroserviceCluster(*args, **kwargs)
    elif settings.deployment_mode == settings.DeploymentMode.KUBERNETES:
        settings.ServiceWaypost.deployment = KubernetesMicroserviceCluster(*args, **kwargs)

    settings.ServiceWaypost.deployment.setup()


def destroy_deployment():
    if settings.deployment_mode == settings.DeploymentMode.ZERO:
        return
    settings.ServiceWaypost.deployment.teardown()
