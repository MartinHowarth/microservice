from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from requests.exceptions import ConnectionError

from microservice.core import settings
from microservice.core.service_waypost import init_service_waypost
from microservice.core.orchestrator import Orchestrator


class TestOrchestratorSimple(TestCase):
    """
    This covers testing that the orchestrator's basic functions work, i.e. on the scale of creating single instances.
    """
    def setUp(self):
        init_service_waypost()
        settings.deployment_type = settings.DeploymentType.ZERO

    @patch("microservice.core.orchestrator.send_to_uri")
    def test_send_management(self, mock_send_to_uri):
        service_name = "test"
        uri = "http://127.0.0.1:5000/%s" % service_name
        action = "action_1"
        args = (5, 6, 7)
        kwargs = {
            'apple': "tasty",
            'banana': "loaf",
        }

        with self.subTest("Test send management"):
            Orchestrator.send_management(uri, action, *args, **kwargs)

            mock_send_to_uri.assert_has_calls([
                call('http://127.0.0.1:5000/__management', __action=action, *args, **kwargs)
            ])

        with self.subTest("Test error on sending management"):
            mock_send_to_uri.side_effect = ConnectionError()
            old_retire_uri = Orchestrator.retire_uri
            mock_retire_uri = MagicMock()
            Orchestrator.retire_uri = mock_retire_uri

            Orchestrator.send_management(uri, action, *args, **kwargs)

            mock_retire_uri.assert_has_calls([
                call(service_name, uri)
            ])
            Orchestrator.retire_uri = old_retire_uri

    @patch("microservice.core.orchestrator.subprocess.Popen")
    @patch("microservice.core.orchestrator.send_to_uri")
    @patch("microservice.core.orchestrator.pubsub.publish")
    def test_create_instance(self, mock_publish, mock_send_to_uri, mock_popen):
        service_name = "test_service"

        with self.subTest(msg="Test creation and all notifications"):
            Orchestrator.create_instance(service_name)
            mock_popen.assert_has_calls([
                call(['microservice', '--host', '127.0.0.1', '--port', '5000', '--local_services', 'test_service'],
                     close_fds=True, creationflags=8)
            ])
            mock_send_to_uri.assert_has_calls([
                call('http://127.0.0.1:5000/__management', 'http://127.0.0.1:4999',
                     'http://127.0.0.1:5000/%s' % service_name, __action='receive_orchestrator_info')
            ])
            mock_publish.assert_has_calls([
                call('test_service', 'http://127.0.0.1:5000/test_service', __action='receive_service_advertisement')
            ])

        with self.subTest(msg="Test multiple creation"):
            Orchestrator.create_instance(service_name)
            Orchestrator.create_instance(service_name + "2")
            mock_publish.assert_has_calls([
                call('test_service', 'http://127.0.0.1:5000/test_service', __action='receive_service_advertisement'),
                call('test_service', 'http://127.0.0.1:5001/test_service', __action='receive_service_advertisement'),
                call('test_service2', 'http://127.0.0.1:5002/test_service2', __action='receive_service_advertisement'),
            ])
