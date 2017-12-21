import pickle
import requests

from unittest import TestCase
from unittest.mock import MagicMock

from microservice.core.service_waypost import init_service_waypost

from microservice.core import service_host


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
    def setUp(self):
        self.mocked_request_result = MockRequestResult()
        self.mocked_requests_get = MagicMock(return_value=self.mocked_request_result)
        requests.get = self.mocked_requests_get

    def mock_setup(self, service_name):
        service_host.configure_microservice()
        init_service_waypost()

        service_host.app.testing = True
        self.app = service_host.app.test_client()
        self.service_name = service_name
        service_host.add_local_service(self.service_name)

    def requests_get_has_pickled_calls(self, calls):
        self.assertEqual(len(self.mocked_requests_get.mock_calls), len(calls))

        for ii, cal in enumerate(calls):
            self.assertTrue('data' in self.mocked_requests_get.mock_calls[ii][2].keys())
            kwargs = self.mocked_requests_get.mock_calls[ii][2]
            data = kwargs.pop('data')

            expected_uri = cal[1][0]
            expected_object = cal[1][1]
            called_uri = self.mocked_requests_get.mock_calls[ii][1][0]
            called_object = pickle.loads(data)

            self.assertEqual(expected_uri, called_uri)

            if isinstance(expected_object, BaseException):
                self.assertEqual(type(expected_object), type(called_object))
                self.assertEqual(expected_object.args, called_object.args)
            else:
                self.assertEqual(expected_object, called_object)
                self.assertEqual(cal[2], kwargs)