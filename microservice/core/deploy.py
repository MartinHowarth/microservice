from typing import List

from microservice.core import settings
from microservice.core.subprocess_deployment import SubprocessDeployment


def create_deployment(microservice_names: List[str]):
    if settings.deployment_mode == settings.DeploymentMode.ZERO:
        return
    elif settings.deployment_mode == settings.DeploymentMode.SUBPROCESS:
        settings.ServiceWaypost.deployment = SubprocessDeployment(microservice_names)
    elif settings.deployment_mode == settings.DeploymentMode.KUBERNETES:
        raise NotImplementedError("not implemented")

    settings.ServiceWaypost.deployment.setup()


def destroy_deployment():
    if settings.deployment_mode == settings.DeploymentMode.ZERO:
        return
    settings.ServiceWaypost.deployment.teardown()
