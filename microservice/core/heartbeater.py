import threading
import time

from collections import namedtuple


ServiceDfn = namedtuple("ServiceDefn", ['service_name', 'uri'])


class HeartBeater:

    heartbeat_running = False
    heartbeater = None
    heartbeat_interval = 1  # seconds between heartbeat to every MS

    percent_idle_high_threshold = 0.7
    percent_idle_low_threshold = 0.3

    congested_services = []
    idle_services = []
    dead_uris = []

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def __del__(self):
        self.stop_heartbeat_checking()

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
        result = self.orchestrator.send_management(uri, "heartbeat")
        print("Heartbeating result is:", result)
        return result

    def heartbeat_service(self, service_name):
        # Cast to list to perform a copy operation so no one can change the list under our feet.
        sum_idle = 0
        service_providers = list(self.orchestrator.service_providers[service_name])
        any_result = False
        for uri in service_providers:
            result = self.heartbeat_uri(uri)

            if not result:
                print("Service %s at uri %s has failed." % (service_name, uri))
                self.dead_uris.append(ServiceDfn(service_name, uri))
                sum_idle -= 1
            else:
                any_result = True
                sum_idle += result["percent_idle"]

        if any_result:
            avg_idle = sum_idle / len(service_providers)
            print("Average idle of service %s is:" % service_name, avg_idle)
            if avg_idle > self.percent_idle_high_threshold:
                self.idle_services.append(service_name)
            if avg_idle < self.percent_idle_low_threshold:
                print("Service %s is congested!" % service_name)
                self.congested_services.append(service_name)

    def check_all_heartbeats(self):
        print("Checking all heartbeats")
        # Cast to list to perform a copy operation so no one can change the list under our feet.
        for service_name in list(self.orchestrator.service_providers.keys()):
            self.heartbeat_service(service_name)

        # TODO
        # This below should actually happen within the orchestrator. I.e. this heartbeater should provide the
        # information, then the orchestrator should collect it periodically and deal with it.

        # Retire any uncontactable (and therefore as good as dead) services.
        for service_definition in self.dead_uris:
            self.orchestrator.retire_uri(service_definition.service_name, service_definition.uri)
        self.dead_uris = []

        # Scale down too-idle services to conserve resources.
        for service_name in self.idle_services:
            self.orchestrator.scale_down(service_name)
        self.idle_services = []

        # Scale up congested services to alleviate congestion.
        for service_name in self.congested_services:
            self.orchestrator.scale_up(service_name)
        self.congested_services = []

    def heartbeat_monitor(self):
        while self.heartbeat_running:
            time.sleep(self.heartbeat_interval)
            self.check_all_heartbeats()
