import copy
import enum
import threading
import time
import requests
import subprocess

from requests.exceptions import ConnectionError

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

    heartbeat_running = False
    heartbeater = None
    heartbeat_interval = 1  # seconds between heartbeat to every MS

    # Not sure if this is even worth keeping.
    spawned_subprocesses = {}

    def __del__(self):
        self.stop_heartbeat_checking()

    @property
    def uri(self):
        return "http://%s:%s" % (self.host, self.port)

    def send_management(self, uri, action, *args, **kwargs):
        service_name = uri.split('/')[-1]
        service_mgmt = uri.replace(service_name, '__management')
        json_data = {
            'action': action,
            '_args': args,
            '_kwargs': kwargs,
        }
        print("Sending management command to service %s at uri %s:" % (service_name, service_mgmt), json_data)
        try:
            result = requests.get(service_mgmt, json=json_data).json()['_args']
        except ConnectionError:
            # If the management connection fails, then declare the MS as dead
            # There is no point heartbeating as that also relies on the management connection.
            self.retire_uri(service_name, uri)
            result = False
        return result

    def locate_service(self, service_name):
        print("Locating service:", service_name)
        if service_name not in self.service_locations.keys() or not self.service_locations[service_name]:
            print("No existing service for %s." % service_name)
            self.create_instance(service_name)

        if self.load_balancer_type == LoadBalancerType.ZERO:
            locations = [self.service_locations[service_name][0]]
        elif self.load_balancer_type == LoadBalancerType.ORCHESTRATOR:
            locations = [next(self.service_locations[service_name])]
        elif self.load_balancer_type == LoadBalancerType.CLIENT:
            locations = self.service_locations[service_name]
        else:
            raise NotImplementedError
        print("Service %s found at:" % service_name, locations)
        return locations

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

    def report_service_failure(self, service_name):
        """
        An MS has reported a failure - check all the services of that type.
        :param service_name:
        :return:
        """
        print("Failure report received about service:", service_name)
        self.heartbeat_service(service_name)

    def start_heartbeat_checking(self):
        self.heartbeat_running = True
        self.heartbeater = threading.Thread(target=self.heartbeat_monitor)
        self.heartbeater.start()

    def stop_heartbeat_checking(self):
        self.heartbeat_running = False
        if self.heartbeater:
            self.heartbeater.join()

    def heartbeat_uri(self, uri):
        print("Heartbeating:", uri)
        result = self.send_management(uri, "heartbeat")
        print("Heartbeating result is:", result)
        return result

    def heartbeat_service(self, service_name):
        dead_uris = []
        # Cast to list to perform a copy operation so no one can change the list under our feet.
        for uri in list(self.service_locations[service_name]):
            if not self.heartbeat_uri(uri):
                print("Service %s at uri %s has failed." % (service_name, uri))
                dead_uris.append(uri)
        for uri in dead_uris:
            self.retire_uri(service_name, uri)

    def check_all_heartbeats(self):
        print("Checking all heartbeats")
        # Cast to list to perform a copy operation so no one can change the list under our feet.
        for service_name in list(self.service_locations.keys()):
            self.heartbeat_service(service_name)

    def heartbeat_monitor(self):
        while self.heartbeat_running:
            self.check_all_heartbeats()
            time.sleep(self.heartbeat_interval)

    def retire_uri(self, service_name, uri):
        try:
            self.service_locations[service_name].remove(uri)
        except ValueError:
            # This catch can be required, for example:
            # If the normal heartbeat is trying to retire the service at the same time as an MS reports a failure
            # then they can both end up trying to remove the same uri.
            pass


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
    'report_service_failure': Orchestrator.report_service_failure,
}


def initialise_orchestration():
    Orchestrator.start_heartbeat_checking()
    app.run(host=Orchestrator.host, port=Orchestrator.port)
