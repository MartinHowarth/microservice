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


class TestOrchestratorCreationAndDeletion(TestCase):
    def setUp(self):
        # Start the orchestrator
        # Disable the heartbeater so we have more control over starting and stopping instances reliably.
        quickstart_orchestrator.main(disable_healthchecking=True)

        # Start the local service waypost
        init_service_waypost(disable_heartbeating=True)
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
                self.assertEqual(len(orchestrator_info['service_providers'].get(service_name, [])), number)

    def assertKnownServicesAre(self, service_name_to_ask, services):
        uris_to_ask = self.get_current_info(Orchestrator.uri)['service_providers'][service_name_to_ask]
        for uri in uris_to_ask:
            for service_name, number in services.items():
                with self.subTest(msg="%s: Check number of known %s is %s" % (uri, service_name, number)):
                    services_info = self.get_current_info(uri)
                    self.assertEqual(len(services_info['service_providers'].get(service_name, [])), number)

    def test_creation_and_deletion(self):
        with self.subTest(msg="Ensure that the correct services are created at initialisation of orchestrator"):
            # Assert that the orchestrator hasn't made any services.
            orchestrator_info = self.get_current_info(Orchestrator.uri)
            self.assertEqual(orchestrator_info, {'service_providers': {}})

        msg = "Ensure that a service is created when it is first asked for"
        with self.subTest(msg=msg):
            # Cause creation of `echo_as_dict`
            echo_as_dict()

            # Leave time for the async creation of the pubsub server to happen
            time.sleep(1)

            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 1,
            })

        msg = "Ensure that a service is not created when it already exists"
        with self.subTest(msg=msg):
            # Ensure we don't create a second `echo_as_dict`
            echo_as_dict()
            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 1,
            })

        msg = "Ensure that a second service can be created."
        with self.subTest(msg=msg):
            # Cause creation of `echo_as_dict2`
            echo_as_dict2()
            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
            })

        msg = "Ensure that nested services can be created."
        with self.subTest(msg=msg):
            # Cause creation of `echo_as_dict4` and `echo_as_dict3`
            # 4 calls into 3, which calls into 2, which calls into 1.
            # 1 and 2 already exist, so we just want 3 and 4 to be created.
            echo_as_dict4()
            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict3': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict4': 1,
            })

            # 5 calls into 2 and 3
            echo_as_dict5()
            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict3': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict4': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict5': 1,
            })

        msg = "Ensure that each service knows about the correct other services"
        with self.subTest(msg=msg):
            # 4 calls into 3, which calls into 2, which calls into 1, so they should each know only one other service
            self.assertKnownServicesAre(
                'microservice.tests.microservices_for_testing.echo_as_dict',
                {
                })
            self.assertKnownServicesAre(
                'microservice.tests.microservices_for_testing.echo_as_dict2',
                {
                    'microservice.tests.microservices_for_testing.echo_as_dict': 1,
                    'microservice.core.pubsub._send_to_pubsub': 1,
                })
            self.assertKnownServicesAre(
                'microservice.tests.microservices_for_testing.echo_as_dict3',
                {
                    'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                    'microservice.core.pubsub._send_to_pubsub': 1,
                })
            self.assertKnownServicesAre(
                'microservice.tests.microservices_for_testing.echo_as_dict4',
                {
                    'microservice.tests.microservices_for_testing.echo_as_dict3': 1,
                    'microservice.core.pubsub._send_to_pubsub': 1,
                })

            with self.subTest(msg="Check that nested services can know about two other existing services"):
                self.assertKnownServicesAre(
                    'microservice.tests.microservices_for_testing.echo_as_dict5',
                    {
                        'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                        'microservice.tests.microservices_for_testing.echo_as_dict3': 1,
                        'microservice.core.pubsub._send_to_pubsub': 1,
                    })

        msg = "Test that if a service is shut down that it is not immediately recreated"
        with self.subTest(msg=msg):
            service_name_to_kill = 'microservice.tests.microservices_for_testing.echo_as_dict3'
            # Kill the first instance of it.
            uri_to_kill = self.get_current_info(Orchestrator.uri)['service_providers'][service_name_to_kill][0]
            self.call_on_orchestrator('destroy_instance', uri_to_kill)

            # Give time for the publishes to finish
            time.sleep(1)

            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict3': 0,
                'microservice.tests.microservices_for_testing.echo_as_dict4': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict5': 1,
            })

            # Make sure that services which use that service are told about the death.
            self.assertKnownServicesAre(
                'microservice.tests.microservices_for_testing.echo_as_dict4',
                {
                    'microservice.tests.microservices_for_testing.echo_as_dict3': 0,
                    'microservice.core.pubsub._send_to_pubsub': 1,
                })

        # Sleep to give time for the killed flask server to actually close...
        time.sleep(2)

        msg = "Test that a shutdown service is recreated when next requested by another MS"
        with self.subTest(msg=msg):
            # 4 calls into 3, so should cause recreation.
            echo_as_dict4()

            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict3': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict4': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict5': 1,
            })

        msg = "Test that a shutdown service is recreated when next requested by external call"
        with self.subTest(msg=msg):
            # Kill the service again
            service_name_to_kill = 'microservice.tests.microservices_for_testing.echo_as_dict3'
            uri_to_kills = self.get_current_info(Orchestrator.uri)['service_providers'][service_name_to_kill]
            print(uri_to_kills)
            uri_to_kill = self.get_current_info(Orchestrator.uri)['service_providers'][service_name_to_kill][0]
            self.call_on_orchestrator('destroy_instance', uri_to_kill)

            # Sleep to give time for the killed flask server to actually close...
            time.sleep(2)

            echo_as_dict3()

            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict3': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict4': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict5': 1,
            })

        msg = "Test that creation of a second MS of an existing type gets advertised correctly"
        with self.subTest(msg=msg):
            # Only 2 uses 1, so 2 and only 2 should get notified
            self.call_on_orchestrator('create_instance', "microservice.tests.microservices_for_testing.echo_as_dict")

            # Leave time for service setup and publish information to be sent.
            time.sleep(1)

            # Check that 2 now knows about 2 instances of 1.
            self.assertKnownServicesAre(
                'microservice.tests.microservices_for_testing.echo_as_dict2',
                {
                    'microservice.tests.microservices_for_testing.echo_as_dict': 2,
                    'microservice.core.pubsub._send_to_pubsub': 1,
                })

            # Make sure that another service isn't told accidentally.
            self.assertKnownServicesAre(
                'microservice.tests.microservices_for_testing.echo_as_dict3',
                {
                    'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                    'microservice.core.pubsub._send_to_pubsub': 1,
                })

        msg = "Test that scaling up works"
        with self.subTest(msg=msg):
            self.call_on_orchestrator('scale_up', "microservice.tests.microservices_for_testing.echo_as_dict")

            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 3,
                'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict3': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict4': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict5': 1,
            })

        msg = "Test that scaling works"
        with self.subTest(msg=msg):
            self.call_on_orchestrator('scale_down', "microservice.tests.microservices_for_testing.echo_as_dict")

            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 2,
                'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict3': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict4': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict5': 1,
            })
            self.call_on_orchestrator('scale_down', "microservice.tests.microservices_for_testing.echo_as_dict")
            self.call_on_orchestrator('scale_down', "microservice.tests.microservices_for_testing.echo_as_dict")
            self.call_on_orchestrator('scale_down', "microservice.tests.microservices_for_testing.echo_as_dict")

            self.assertServicesExist(msg, {
                'microservice.core.pubsub._send_to_pubsub': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict': 0,
                'microservice.tests.microservices_for_testing.echo_as_dict2': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict3': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict4': 1,
                'microservice.tests.microservices_for_testing.echo_as_dict5': 1,
            })
