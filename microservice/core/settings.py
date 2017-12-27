import enum
import flask
import logging
import threading


class Mode(enum.Enum):
    ACTOR = "ACTOR"
    SYN = "SYN"
    ZERO = "ZERO"


class LoggingMode(enum.Enum):
    HUMAN = "HUMAN"
    STDOUT = "STDOUT"
    FILE = "FILE"
    FLUENTD = "FLUENTD"
    LOGSTASH = "LOGSTASH"


kube_namespace = "pycroservices"

deployment_mode = Mode.ACTOR
orchestrator_uri = None
this_is_orchestrator = False

ServiceWaypost = None  # type: _ServiceWaypost

thread_locals = threading.local()


def current_message():
    if deployment_mode == Mode.SYN:
        if flask.has_app_context() and 'current_message' in flask.g:
            return flask.g.current_message
    elif deployment_mode == Mode.ACTOR:
        if hasattr(thread_locals, "current_message") and thread_locals.current_message is not None:
            return thread_locals.current_message
    return None


def current_request_id():
    msg = current_message()
    if msg is not None:
        return msg.request_id
    return None


# Logging configuration
logging_level = logging.DEBUG

logging_modes = [
    LoggingMode.STDOUT,
]

fluentd_settings = {
    'host': 'localhost',
    'port': 24224,
}

logstash_settings = {
    'host': 'localhost',
    'port': 5959,
    'database_path': 'logstash.db',
}
