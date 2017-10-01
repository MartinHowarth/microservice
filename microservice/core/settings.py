import enum


class DeploymentType(enum.Enum):
    ZERO = "ZERO"
    LOCAL = "LOCAL"
    DOCKER = "DOCKER"


deployment_type = DeploymentType.LOCAL
orchestrator_uri = None
this_is_orchestrator = False

ServiceWaypost = None  # type: _ServiceWaypost
Stethoscope = None  # type: _Stethoscope
