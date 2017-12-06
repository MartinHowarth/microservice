import enum


class DeploymentType(enum.Enum):
    ZERO = "ZERO"
    FLASK = "FLASK"
    GUNICORN = "GUNICORN"
    DOCKER = "DOCKER"


class Mode(enum.Enum):
    SYN = "SYN"
    ACTOR = "ACTOR"


kube_namespace = "pycroservices"

deployment_mode = Mode.ACTOR
deployment_type = DeploymentType.FLASK
orchestrator_uri = None
this_is_orchestrator = False

ServiceWaypost = None  # type: _ServiceWaypost
Stethoscope = None  # type: _Stethoscope
