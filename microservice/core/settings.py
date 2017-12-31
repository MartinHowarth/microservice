import asyncio
import enum
import flask
import logging
import threading


class CommunicationMode(enum.Enum):
    ACTOR = "ACTOR"
    SYN = "SYN"


class LoggingMode(enum.Enum):
    HUMAN = "HUMAN"
    STDOUT = "STDOUT"
    FILE = "FILE"
    FLUENTD = "FLUENTD"
    LOGSTASH = "LOGSTASH"


class DeploymentMode(enum.Enum):
    KUBERNETES = "KUBERNETES"
    SUBPROCESS = "SUBPROCESS"
    ZERO = "ZERO"


kube_namespace = "pycroservices"

communication_mode = CommunicationMode.ACTOR
deployment_mode = DeploymentMode.SUBPROCESS

all_microservices = []

ServiceWaypost = None  # type: _ServiceWaypost

flask_app_thread = None

thread_locals = threading.local()

event_loop = asyncio.get_event_loop()

interface_results = dict()
interface_requests = dict()

local_uri = None  # type: str


def set_interface_result(key, value):
    interface_results[key] = value


def set_interface_request(request_id, result_key: str):
    """
    Set a flag to say that we're expecting a response to the request with the given request_id.
    :param request_id:
    :param result_key
    """
    interface_requests[request_id] = result_key


def current_message():
    if communication_mode == CommunicationMode.SYN:
        if flask.has_app_context() and 'current_message' in flask.g:
            return flask.g.current_message
    elif communication_mode == CommunicationMode.ACTOR:
        if hasattr(thread_locals, "current_message") and thread_locals.current_message is not None:
            return thread_locals.current_message
    return None


def current_request_id():
    msg = current_message()
    if msg is not None:
        return msg.request_id
    return None


def set_current_message(message):
    if communication_mode == CommunicationMode.SYN:
        flask.g.current_message = message
    elif communication_mode == CommunicationMode.ACTOR:
        thread_locals.current_message = message


# Logging configuration
logging_level = logging.DEBUG

logging_modes = [
    # LoggingMode.STDOUT,
    LoggingMode.HUMAN,
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
