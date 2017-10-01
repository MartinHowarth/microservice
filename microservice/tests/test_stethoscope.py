import time

from unittest import TestCase
from unittest.mock import MagicMock, patch, call

from microservice.core import settings
from microservice.core.orchestrator import Orchestrator
from microservice.core.service_waypost import init_service_waypost
from microservice.core.stethoscope import _Stethoscope


class TestStethoscope(TestCase):
    def setUp(self):
        # # Start the orchestrator
        # quickstart_orchestrator.main(disable_healthchecking=True)

        # Start the local service waypost
        init_service_waypost(disable_heartbeating=True)
        settings.ServiceWaypost.orchestrator_uri = Orchestrator.uri

        self.mock_send_to_orchestrator = MagicMock()
        settings.ServiceWaypost.send_to_orchestrator = self.mock_send_to_orchestrator

        _Stethoscope.heartbeat_timeout = 10000000
        settings.Stethoscope = _Stethoscope()

    @patch("microservice.core.stethoscope.time.time")
    def test_health_checking(self, mock_time):
        mock_time.return_value = 100
        uri_1 = "http://127.0.0.1:4000/service_1"
        uri_1_2 = "http://127.0.0.1:4001/service_1"

        with self.subTest(msg="Test basic heartbeat"):
            settings.Stethoscope.receive_heartbeat(uri_1, {
                'percent_idle': 0.5
            })

            self.assertEqual(settings.Stethoscope.uri_status[uri_1], {
                'percent_idle': 0.5,
                'received_time': 100
            })

            # Allow time for stethoscope to parse the info
            time.sleep(settings.Stethoscope.assessment_interval * 3)

            self.mock_send_to_orchestrator.assert_has_calls([
                call('is_uri_known', uri_1),
            ])

        with self.subTest(msg="Test service idle"):
            settings.Stethoscope.receive_heartbeat(uri_1, {
                'percent_idle': 0.9
            })
            settings.Stethoscope.receive_heartbeat(uri_1_2, {
                'percent_idle': 0.9
            })

            # Allow time for stethoscope to parse the info
            time.sleep(settings.Stethoscope.assessment_interval * 3)

            self.mock_send_to_orchestrator.assert_has_calls([
                call('is_uri_known', uri_1),
                call('is_uri_known', uri_1_2),
                call('scale_down', "service_1", 0.9),
            ], any_order=True)

        with self.subTest(msg="Test service congested"):
            settings.Stethoscope.receive_heartbeat(uri_1, {
                'percent_idle': 0.1
            })
            settings.Stethoscope.receive_heartbeat(uri_1_2, {
                'percent_idle': 0.1
            })

            # Allow time for stethoscope to parse the info
            time.sleep(settings.Stethoscope.assessment_interval * 3)

            self.mock_send_to_orchestrator.assert_has_calls([
                call('is_uri_known', uri_1),
                call('is_uri_known', uri_1_2),
                call('scale_up', "service_1", 0.1),
            ], any_order=True)

        settings.Stethoscope.receive_heartbeat(uri_1, {
            'percent_idle': 0.5
        })
        settings.Stethoscope.receive_heartbeat(uri_1_2, {
            'percent_idle': 0.5
        })

        with self.subTest(msg="Test heartbeat faliure"):
            # Set the timeout short and then "advance time" by changing the mock's return value.
            settings.Stethoscope.heartbeat_timeout = 1
            mock_time.return_value = 110

            time.sleep(settings.Stethoscope.assessment_interval * 3)
            self.mock_send_to_orchestrator.assert_has_calls([
                call('heartbeat_failed', uri_1),
                call('heartbeat_failed', uri_1_2),
            ], any_order=True)
