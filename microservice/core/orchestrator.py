import enum
import requests
import subprocess

from collections import defaultdict
from flask import Flask, request, jsonify

from microservice.core.load_balancer import LocalLoadBalancer


DETACHED_PROCESS = 8

app = Flask(__name__)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


class LoadBalancerType(enum.Enum):
    ZERO = "ZERO"
    ORCHESTRATOR = "ORCHESTRATOR"
    CLIENT = "CLIENT"


class _Orchestrator:
    """
    This is a microservice that provides function to other microservices of:
        - Dicoverability of existing microservices
        - Creation of non-existent microservices
        - Health monitoring of microservices
        - Scaling of microservices

    """
    host = "127.0.0.1"
    port = 4999

    next_service_port = 5000
    service_locations = defaultdict(LocalLoadBalancer)

    load_balancer_type = LoadBalancerType.CLIENT

    # Not sure if this is even worth keeping.
    spawned_subprocesses = {}

    @property
    def uri(self):
        return "http://%s:%s" % (self.host, self.port)

    def locate_service(self, service_name):
        print("Locating service:", service_name)
        if service_name not in self.service_locations.keys():
            print("No existing service for %s." % service_name)
            self.create_instance(service_name)
            self.create_instance(service_name)
        return {
            LoadBalancerType.ZERO: [self.service_locations[service_name][0]],
            LoadBalancerType.ORCHESTRATOR: [next(self.service_locations[service_name])],
            LoadBalancerType.CLIENT: self.service_locations[service_name],
        }[self.load_balancer_type]

    def create_instance(self, service_name):
        uri = "http://%s:%s/%s" % (self.host, self.next_service_port, service_name)
        service_cmd = "microservice --host %s --port %s --local_services %s" % (
            self.host, self.next_service_port, service_name)
        service_cmd = service_cmd.split(' ')
        self.next_service_port += 1

        print("Spawning new service with cmd:", service_cmd)
        new_service = subprocess.Popen(service_cmd, creationflags=DETACHED_PROCESS, close_fds=True)
        self.spawned_subprocesses[service_name] = new_service

        print("New service spawned with uri:", uri)
        self.service_locations[service_name].append(uri)

        self.send_management(uri, "set_orchestrator", self.uri)

    def send_management(self, uri, action, *args, **kwargs):
        service_name = uri.split('/')[-1]
        service_mgmt = uri.replace(service_name, '__management')
        json_data = {
            'action': action,
            '_args': args,
            '_kwargs': kwargs,
        }
        print("Sending management command to service %s at uri %s:" % (service_name, service_mgmt), json_data)
        requests.get(service_mgmt, json=json_data)


Orchestrator = _Orchestrator()


@app.route("/")
def orchestration():
    """
    General interface for the external forces to manage this microservice.

    This is the interface that the Orchestrator uses.
    """
    management_json = request.get_json()
    if management_json:
        print("Received management request:", management_json)
        action = management_json.get('action', None)
        args = management_json.get('_args', [])
        kwargs = management_json.get('_kwargs', {})
        if action in management_waypost.keys():
            result = management_waypost[action](*args, **kwargs)
        else:
            raise InvalidUsage("The requested management action `%s` does not exist." % action)
    else:
        raise InvalidUsage("There was no json included in the management request.")
    return jsonify({'_args': result})


management_waypost = {
    'locate_service': Orchestrator.locate_service,
}


def initialise_orchestration():
    app.run(host=Orchestrator.host, port=Orchestrator.port)
