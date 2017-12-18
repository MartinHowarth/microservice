import json
import requests
import time

from unittest.mock import MagicMock, call, patch
from unittest import TestCase

from microservice.core import settings, communication
from microservice.core.service_waypost import init_service_waypost

from microservice.core import service_host


class MockRequestResult(MagicMock):
    _json_args = (2, 3, 4)

    def json(self):
        return {
            'args': self._json_args
        }


class TestAsynchronousLocalService(TestCase):
    @classmethod
    def setUpClass(cls):
        service_host.configure_microservice()
        init_service_waypost()
        settings.deployment_mode = settings.Mode.ACTOR

        cls.mocked_request_result = MockRequestResult()
        cls.mocked_requests_get = MagicMock(return_value=cls.mocked_request_result)
        requests.get = cls.mocked_requests_get

        service_host.app.testing = True
        cls.app = service_host.app.test_client()
        cls.service_name = "microservice.tests.microservices_for_testing.echo_as_dict"
        service_host.add_local_service(cls.service_name)

        cls.args = (1, 2, 3)
        cls.kwargs = {'a': 'asdf', 'b': 123}
        cls.test_msg = communication.construct_message(
            "local_service_name",
            communication.Message(
                results={
                    'previous_service_name': [1, 3, 5, 7]
                }
            ),
            *cls.args,
            **cls.kwargs,
        )

    def test_request(self):
        response = self.app.get(
            '/',
            data=json.dumps(self.test_msg.to_dict),
            content_type='application/json')
        result = json.loads(response.data.decode('utf-8'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, True)
        # Wait for the thread pool to complete the work.
        time.sleep(1)
        self.mocked_requests_get.assert_has_calls([
            call('http://local-service-name.pycroservices/',
                 json={
                     'args': [],
                     'kwargs': {},
                     'via': [],
                     'results': {
                         'previous_service_name': [1, 3, 5, 7],
                         'local_service_name': {'_args': self.args,
                                                **self.kwargs}
                     }
                 }),
        ])
