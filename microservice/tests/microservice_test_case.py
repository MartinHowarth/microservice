import pickle
from unittest import TestCase
from unittest.mock import MagicMock

from microservice.core.service_waypost import init_service_waypost

from microservice.core import service_host, communication


class MockRequestResult(MagicMock):
    args = (2, 3, 4)

    def json(self):
        return {
            'args': self.args
        }

    @property
    def content(self):
        return pickle.dumps(self.args)


class MicroserviceTestCase(TestCase):
    original_send_object_to_service = None

    def setUp(self):
        self.original_send_object_to_service = communication.send_object_to_service

        self.mocked_request_result = MockRequestResult()
        self.mocked_send_object_to_service = MagicMock(
            return_value=self.mocked_request_result.args)
        communication.send_object_to_service = self.mocked_send_object_to_service

    def tearDown(self):
        communication.send_object_to_service = self.original_send_object_to_service

    def mock_setup(self, service_name):
        service_host.configure_microservice()
        init_service_waypost()

        service_host.app.testing = True
        self.app = service_host.app.test_client()
        self.service_name = service_name
        service_host.add_local_service(self.service_name)
