import time

from unittest import TestCase

from microservice import quickstart_orchestrator

from microservice.core import settings
from microservice.core.communication import send_to_mgmt_of_uri
from microservice.core.orchestrator import Orchestrator
from microservice.core.service_waypost import init_service_waypost

from microservice.tests.microservices_for_testing import (
    echo_as_dict, echo_as_dict2, echo_as_dict3, echo_as_dict4, echo_as_dict5
)


class TestHealthChecking(TestCase):
    def setUp(self):
        # Start the orchestrator
        quickstart_orchestrator.main()

        # Start the local service waypost
        init_service_waypost()
        settings.ServiceWaypost.orchestrator_uri = Orchestrator.uri

    def call_on_orchestrator(self, action, *args, **kwargs):
        return settings.ServiceWaypost.send_to_orchestrator('__TEST__' + action, *args, **kwargs)

    def get_current_info(self, uri):
        return send_to_mgmt_of_uri(uri, __action='current_deployment_information')

    def assertServicesExist(self, msg, services):
        """
        :param str msg:
        :param dict[str, int] services: Dict of service_name: expected number to exist.
        """
        for service_name, number in services.items():
            with self.subTest(msg=msg + ": Check number of existing %s is %s" % (service_name, number)):
                orchestrator_info = self.get_current_info(Orchestrator.uri)
                print(orchestrator_info)
                print("Getting:", service_name)
                print("Got:", orchestrator_info['service_providers'].get(service_name, []))
                self.assertEqual(len(orchestrator_info['service_providers'].get(service_name, [])), number)

    def assertKnownServicesAre(self, service_name_to_ask, services):
        uris_to_ask = self.get_current_info(Orchestrator.uri)['service_providers'][service_name_to_ask]
        for uri in uris_to_ask:
            for service_name, number in services.items():
                with self.subTest(msg="%s: Check number of known %s is %s" % (uri, service_name, number)):
                    services_info = self.get_current_info(uri)
                    print(services_info)
                    print("Getting:", service_name)
                    print("Got:", services_info['service_providers'].get(service_name, []))
                    self.assertEqual(len(services_info['service_providers'].get(service_name, [])), number)

    def test_health_checking(self):
        pass