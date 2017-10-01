import threading
import time

from collections import namedtuple, defaultdict

from microservice.core import settings
from microservice.core.decorator import microservice
from microservice.core.service_functions import service_uri_information

ServiceIdle = namedtuple("ServiceIdle", ['service_name', 'avg_idle'])


class _Stethoscope:
    congested_services = set()
    idle_services = set()
    dead_uris = set()
    suspect_uris = set()
    unknown_uris = set()

    uri_status = dict()

    running = False
    _heartbeat_assessor = None
    assessment_interval = 0.1  # Seconds between assessing all heartbeat information
    heartbeat_timeout = 2  # Seconds allowed between heartbeats from a MS before treating is as dead.

    _orchestrator_talker = None

    percent_idle_high_threshold = 0.7
    percent_idle_low_threshold = 0.3

    def __init__(self):
        self.running = True
        self._heartbeat_assessor = threading.Thread(target=self.assess_heartbeats)
        self._heartbeat_assessor.start()

        self._orchestrator_talker = threading.Thread(target=self.orchestrator_talker)
        self._orchestrator_talker.start()

    def receive_heartbeat(self, originating_uri, heartbeat_info):
        if not originating_uri:
            return

        if originating_uri not in self.uri_status.keys():
            # If it doesn't exist, then it's either new; or an old MS that's recovered. Ask the orchestrator to find out
            # In the second case, we want to tell the orchestrator about it.
            self.suspect_uris.add(originating_uri)

        heartbeat_info.update({
            'received_time': time.time()
        })
        self.uri_status[originating_uri] = heartbeat_info

    def assess_heartbeats(self):
        while self.running:
            time.sleep(self.assessment_interval)
            idle_by_service = defaultdict(list)
            current_time = time.time()
            for uri, info in self.uri_status.items():
                # Check if the last received heartbeat was too old.
                if current_time - info['received_time'] > self.heartbeat_timeout:
                    self.dead_uris.add(uri)
                    print("Dead heartbeat for:", uri)
                    continue
                uri_info = service_uri_information(uri)
                idle_by_service[uri_info.service_name].append(info['percent_idle'])

            for dead_uri in self.dead_uris:
                del self.uri_status[dead_uri]

            for service_name, idle_pcts in idle_by_service.items():
                avg_idle = sum(idle_pcts) / len(idle_pcts)
                print("Average idle of service %s is:" % service_name, avg_idle)
                if avg_idle > self.percent_idle_high_threshold and len(idle_pcts) > 1:
                    # Don't mark as idle if there is only one instance of the service.
                    self.idle_services.add(ServiceIdle(service_name, avg_idle))
                if avg_idle < self.percent_idle_low_threshold:
                    print("Service %s is congested!" % service_name)
                    self.congested_services.add(ServiceIdle(service_name, avg_idle))

    def orchestrator_talker(self):
        while self.running:
            time.sleep(self.assessment_interval)
            # Investigate any suspect URIs
            while self.suspect_uris:
                uri = self.suspect_uris.pop()
                if not settings.ServiceWaypost.send_to_orchestrator('is_uri_known', uri):
                    self.unknown_uris.add(uri)

            # Deal with any unknown URIs
            while self.unknown_uris:
                uri = self.unknown_uris.pop()
                settings.ServiceWaypost.send_to_orchestrator('heartbeat_from_unknown_uri', uri)

            # Deal with any dead uris
            while self.dead_uris:
                uri = self.dead_uris.pop()
                settings.ServiceWaypost.send_to_orchestrator('heartbeat_failed', uri)

            # Deal with any too-idle services
            while self.idle_services:
                service_idle = self.idle_services.pop()  # type: ServiceIdle
                settings.ServiceWaypost.send_to_orchestrator('scale_down',
                                                             service_idle.service_name,
                                                             service_idle.avg_idle)

            # Deal with any too-congested services
            while self.congested_services:
                service_idle = self.congested_services.pop()  # type: ServiceIdle
                settings.ServiceWaypost.send_to_orchestrator('scale_up',
                                                             service_idle.service_name,
                                                             service_idle.avg_idle)


@microservice
def notify_stethoscope(uri, heartbeat_info):
    if not settings.Stethoscope:
        settings.Stethoscope = _Stethoscope()
    settings.Stethoscope.receive_heartbeat(uri, heartbeat_info)
