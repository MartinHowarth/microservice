import enum
import json
import subprocess
import sys
import threading
import time

from requests.exceptions import ConnectionError

from collections import defaultdict
from flask import Flask, request, jsonify

from microservice.core.communication import send_to_mgmt_of_uri
from microservice.core.load_balancer import LocalLoadBalancer
from microservice.core.service_functions import service_uri_information
from microservice.core import pubsub
from microservice.core import settings


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
    # service_consumers = defaultdict(list)  # Dict of {service_name: list(uris who consume it)}

    load_balancer_type = LoadBalancerType.CLIENT

    # Not sure if this is even worth keeping.
    spawned_subprocesses = {}

    subprocess_additional_kwargs = {}

    to_publish_queue = []
    publisher_thread = None
    publish_interval = 0.1

    running = True

    _disable_healthchecking = False

    def start(self, disable_healthchecking=None, **kwargs):
        """

        :param kwargs: Arguments can be passed in this way from the command line.
        :return:
        """
        if disable_healthchecking is not None:
            self._disable_healthchecking = disable_healthchecking

        if self._disable_healthchecking:
            self.subprocess_additional_kwargs = json.dumps({
                'disable_heartbeating': True,
            })

        self.running = True

        self.publisher_thread = threading.Thread(target=self.send_publishes)
        self.publisher_thread.start()

    def send_publishes(self):
        while self.running:
            while self.to_publish_queue:
                # Take from the front of the queue.
                publish = self.to_publish_queue.pop(0)
                print("Actually publishing:", publish)
                pubsub.publish(*publish['args'], **publish['kwargs'])
            time.sleep(self.publish_interval)

    def queue_for_publishing(self, *args, **kwargs):
        """
        Queue events for publishing. This is Async because then we can respond to the immediate query that caused
        the need for the publish, then actually publish the information.
        :param args:
        :param kwargs:
        :return:
        """
        self.to_publish_queue.append({
            'args': args,
            'kwargs': kwargs
        })

    @property
    def uri(self):
        return "http://%s:%s" % (self.host, self.port)

    def send_management(self, uri, action, *args, **kwargs):
        print("Send management:", uri, action, args, kwargs)
        try:
            result = send_to_mgmt_of_uri(uri, __action=action, *args, **kwargs)
        except ConnectionError:
            # If the management connection fails, then declare the MS as dead
            # There is no point heartbeating as that also relies on the management connection.
            self.retire_uri(uri)
            result = False
        return result

    def locate_provider(self, service_name, consumer):
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
        return providers

    def create_instance(self, service_name):
        uri = "http://%s:%s/%s" % (self.host, self.next_service_port, service_name)
        service_cmd = "microservice --host %s --port %s --local_services %s" % (
            self.host, self.next_service_port, service_name)
        service_cmd = service_cmd.split(' ')
        self.next_service_port += 1

        if self.subprocess_additional_kwargs:
            service_cmd.extend(['--other_kwargs', self.subprocess_additional_kwargs])

        print("Spawning new service with cmd:", service_cmd)
        new_service = subprocess.Popen(service_cmd, creationflags=DETACHED_PROCESS, close_fds=True)
        self.spawned_subprocesses[service_name] = new_service

        print("New service spawned with uri:", uri)
        self.service_providers[service_name].append(uri)

        self.send_management(uri, "receive_orchestrator_info", self.uri, uri)
        self.queue_for_publishing(service_name, service_name, uri, __action='receive_service_advertisement')

    def destroy_instance(self, uri):
        print("Shutting down instance:", uri)
        self.send_management(uri, "shut_down")
        self.retire_uri(uri)

    def scale_down(self, service_name, pct_idle=None):
        # TODO allow user config of "always keep N instances of X up"
        if len(self.service_providers[service_name]):
            print("Scaling down service:", service_name)
            uri = self.service_providers[service_name][0]  # Kill the first one created. It's unlucky for some reason.
            self.destroy_instance(uri)

    def scale_up(self, service_name, pct_idle=None):
        print("Scaling up service:", service_name)
        self.create_instance(service_name)

    def report_service_failure(self, service_name):
        """
        An MS has reported a failure.

        TODO: Not sure what to here right now. This could either by a random failure that the healthcheck should
        pick up; or just a broken code path, about which we can do nothing.
        Therefore do nothing, but in the future we could be more proactive than waiting for the healthcheck.

        :param service_name:
        :return:
        """
        print("Failure report received about service:", service_name)
        return True

    def retire_uri(self, uri):
        service_name = service_uri_information(uri).service_name
        try:
            self.service_providers[service_name].remove(uri)
            self.queue_for_publishing(service_name, service_name, uri, __action='receive_service_retirement')
        except ValueError:
            # This catch can be required, for example:
            # If the normal heartbeat is trying to retire the service at the same time as an MS reports a failure
            # then they can both end up trying to remove the same uri.
            pass

    def current_deployment_information(self):
        info = {
            'service_providers': self.service_providers,
        }
        print("current_deployment_information is:", info)
        return info

    def is_uri_known(self, uri):
        service_name = service_uri_information(uri).service_name
        return service_name in self.service_providers.keys() and uri in self.service_providers[service_name]

    def heartbeat_from_unknown_uri(self, uri):
        self.retire_uri(uri)

    def heartbeat_failed(self, uri):
        self.retire_uri(uri)

    # def notify_consumers(self, service_name, uri, retired=False):
    #     print("Notifying consumers about:", service_name, uri, retired)
        # if service_name == self.pub_sub_name:
        #     print("Not notifying about pubsub service")
        #     return
        # consumers = self.service_consumers[service_name]
        # for consumer in consumers:
        #     if retired:
        #         self.send_management(consumer, 'receive_service_retirement', service_name, uri)
        #     else:
        #         self.send_management(consumer, 'receive_service_advertisement', service_name, uri)


Orchestrator = _Orchestrator()


@app.route("/__management")
def orchestration():
    """
    General interface for the external forces to manage this microservice.

    This is the interface that the Orchestrator uses.
    """
    print("Received request:", request)
    management_json = request.get_json()
    if management_json:
        print("Received management request:", management_json)
        action = management_json.get('action', None)
        args = management_json.get('_args', [])
        kwargs = management_json.get('_kwargs', {})
        if action in management_waypost.keys():
            result = management_waypost[action](*args, **kwargs)
        else:
            if action.startswith('__TEST__'):
                # Expose all functions so they can be triggered by a test function.
                func = getattr(Orchestrator, action[len('__TEST__'):])
                result = func(*args, **kwargs)
            else:
                raise InvalidUsage("The requested management action `%s` does not exist." % action)
    else:
        raise InvalidUsage("There was no json included in the management request.")
    return jsonify({'_args': result})


management_waypost = {
    'locate_provider': Orchestrator.locate_provider,
    'report_service_failure': Orchestrator.report_service_failure,
    'current_deployment_information': Orchestrator.current_deployment_information,
    'is_uri_known': Orchestrator.is_uri_known,
    'heartbeat_from_unknown_uri': Orchestrator.heartbeat_from_unknown_uri,
    'heartbeat_failed': Orchestrator.heartbeat_failed,
    'scale_up': Orchestrator.scale_up,
    'scale_down': Orchestrator.scale_down,
}


def initialise_orchestration(disable_healthchecking=None, **kwargs):
    from microservice.core.service_waypost import init_service_waypost
    init_service_waypost(disable_heartbeating=disable_healthchecking)

    Orchestrator.start(disable_healthchecking=disable_healthchecking, **kwargs)
    settings.ServiceWaypost.orchestrator_uri = Orchestrator.uri
    # For now just set the local uri to be ORCHESTRATOR so that we can distinguish in the logs (otherwise it's None)
    # This will need changing when orchestrator robustness is developed.
    settings.ServiceWaypost.local_uri = '/'.join((Orchestrator.uri, "ORCHESTRATOR"))
    print("Starting orchestrator on:", Orchestrator.uri)
    app.run(host=Orchestrator.host, port=Orchestrator.port, threaded=True)
