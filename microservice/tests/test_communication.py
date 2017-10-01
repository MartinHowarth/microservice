import requests

from unittest import TestCase
from unittest.mock import MagicMock, call

from microservice.core.communication import send_to_uri


class MockRequestResult(MagicMock):
    _json_args = (2, 3, 4)

    def json(self):
        return {
            '_args': self._json_args
        }


class TestCommunication(TestCase):
    def setUp(self):
        self.mocked_request_result = MockRequestResult()
        self.mocked_requests_get = MagicMock(return_value=self.mocked_request_result)
        requests.get = self.mocked_requests_get

    def test_send_to_uri(self):
        with self.subTest(msg="Test sending."):
            args = (5, 6, 7)
            kwargs = {
                'apple': "tasty",
                'banana': "loaf",
            }
            uri = "http://127.0.0.1:5000/test"
            action = "test_action"

            send_to_uri(uri, *args, **kwargs)
            send_to_uri(uri, __action=action, *args, **kwargs)
            send_to_uri(uri, *args, __action=action, **kwargs)

            json_data_1 = {
                '_args': args,
                '_kwargs': kwargs,
                'action': None,
            }
            json_data_2 = {
                '_args': args,
                '_kwargs': kwargs,
                'action': action,
            }

            self.mocked_requests_get.assert_has_calls([
                call(uri, json=json_data_1),
                call(uri, json=json_data_2),
                call(uri, json=json_data_2),
            ])

        with self.subTest(msg="Test parsing response"):
            result = send_to_uri(uri, *args, **kwargs)
            self.assertEqual(result, MockRequestResult().json()['_args'])
