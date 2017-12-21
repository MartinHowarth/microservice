import enum
import threading


class Mode(enum.Enum):
    ACTOR = "ACTOR"
    SYN = "SYN"
    ZERO = "ZERO"


kube_namespace = "pycroservices"

deployment_mode = Mode.ACTOR
orchestrator_uri = None
this_is_orchestrator = False

ServiceWaypost = None  # type: _ServiceWaypost

current_message = threading.local()
