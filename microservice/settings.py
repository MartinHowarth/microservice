import enum


class DeploymentType(enum.Enum):
    ZERO = "ZERO"
    LOCAL = "LOCAL"
    DOCKER = "DOCKER"


deployment_type = DeploymentType.LOCAL
this_service = None
