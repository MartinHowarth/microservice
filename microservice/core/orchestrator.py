import enum
import requests
import subprocess

from requests.exceptions import ConnectionError

from collections import defaultdict
from flask import Flask, request, jsonify

from microservice.core.heartbeater import HeartBeater
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
    service_providers = defaultdict(LocalLoadBalancer)  # Dict of {service_name: list(uris who provide it)}
    service_consumers = defaultdict(list)  # Dict of {service_name: list(uris who consume it)}

    load_balancer_type = LoadBalancerType.CLIENT

    # Not sure if this is even worth keeping.
    spawned_subprocesses = {}

    heartbeater = None

    def start(self):
        self.heartbeater = HeartBeater(self)
        self.heartbeater.start_heartbeat_checking()

    @property
    def uri(self):
        return "http://%s:%s" % (self.host, self.port)

    def send_management(self, uri, action, *args, **kwargs):
        print("Send management:", uri, action, args, kwargs)
        service_name = uri.split('/')[-1]
        service_mgmt = uri.replace(service_name, '__management')
        json_data = {
            'action': action,
            '_args': args,
            '_kwargs': kwargs,
        }
        print("Sending management command to service %s at uri %s:" % (service_name, service_mgmt), json_data)
        try:
            result = requests.get(service_mgmt, json=json_data)
            if result:
                result = result.json()['_args']
        except ConnectionError:
            # If the management connection fails, then declare the MS as dead
            # There is no point heartbeating as that also relies on the management connection.
            self.retire_uri(service_name, uri)
            result = False
        return result

    def locate_provider(self, service_name, consumer):
        # If an existing consumer of a service is asking for a provider, then we must assume that they know nothing and
        # therefore treat them as a new consumer - so purge them from the consumer records for the requested service.
        if consumer in self.service_consumers[service_name]:
            self.service_consumers[service_name].remove(consumer)

        print("Locating service %s for consumer:" % service_name, consumer)
        if service_name not in self.service_providers.keys() or not self.service_providers[service_name]:
            print("No existing service for %s." % service_name)
            self.create_instance(service_name)

        if self.load_balancer_type == LoadBalancerType.ZERO:
            providers = [self.service_providers[service_name][0]]
        elif self.load_balancer_type == LoadBalancerType.ORCHESTRATOR:
            providers = [next(self.service_providers[service_name])]
        elif self.load_balancer_type == LoadBalancerType.CLIENT:
            providers = self.service_providers[service_name]
        else:
            raise NotImplementedError
        print("Service %s provided by:" % service_name, providers)
        if consumer:
            self.service_consumers[service_name].append(consumer)
        return providers

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
        self.service_providers[service_name].append(uri)

        self.send_management(uri, "receive_orchestrator_info", self.uri, uri)
        self.notify_consumers(service_name, uri)

    def destroy_instance(self, service_name, uri):
        print("Shutting down instance:", uri)
        self.send_management(uri, "shut_down")
        self.retire_uri(service_name, uri)

    def scale_down(self, service_name):
        # Always leave at least one instance of each service up.
        if len(self.service_providers[service_name]) > 1:
            print("Scaling down service:", service_name)
            uri = self.service_providers[service_name][0]  # Kill the first one created. It's unlucky for some reason.
            self.destroy_instance(service_name, uri)

    def scale_up(self, service_name):
        print("Scaling up service:", service_name)
        self.create_instance(service_name)

    def report_service_failure(self, service_name):
        """
        An MS has reported a failure - check all the services of that type.
        :param service_name:
        :return:
        """
        print("Failure report received about service:", service_name)
        self.heartbeater.heartbeat_service(service_name)

    def retire_uri(self, service_name, uri):
        # TODO: this should be able to work with just the URI - i.e. shouldn't have to specify the service_name.
        try:
            self.service_providers[service_name].remove(uri)
            for service in list(self.service_consumers.keys()):
                if uri in self.service_consumers[service]:
                    self.service_consumers[service].remove(uri)
            print("consumers:", self.service_consumers[service_name])
            self.notify_consumers(service_name, uri, retired=True)
        except ValueError:
            # This catch can be required, for example:
            # If the normal heartbeat is trying to retire the service at the same time as an MS reports a failure
            # then they can both end up trying to remove the same uri.
            pass

    def notify_consumers(self, service_name, uri, retired=False):
        print("Notifying consumers about:", service_name, uri, retired)
        consumers = self.service_consumers[service_name]
        for consumer in consumers:
            if retired:
                self.send_management(consumer, 'receive_service_retirement', service_name, uri)
            else:
                self.send_management(consumer, 'receive_service_advertisement', service_name, uri)


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
    'locate_provider': Orchestrator.locate_provider,
    'report_service_failure': Orchestrator.report_service_failure,
}


def initialise_orchestration():
    Orchestrator.start()
    app.run(host=Orchestrator.host, port=Orchestrator.port)
