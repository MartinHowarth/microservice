import enum

from microservice.core import service_waypost


class DeploymentType(enum.Enum):
    ZERO = "ZERO"
    LOCAL = "LOCAL"
    DOCKER = "DOCKER"


deployment_type = DeploymentType.LOCAL

local_waypost = service_waypost.ServiceWaypost()
