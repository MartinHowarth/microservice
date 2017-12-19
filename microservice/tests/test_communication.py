import pickle
import requests

from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from microservice.core import communication


class MockRequestResult(MagicMock):
    _json_args = (2, 3, 4)

    def json(self):
        return {
            'args': self._json_args
        }

    @property
    def content(self):
        return pickle.dumps(self._json_args)


class TestCommunication(TestCase):
    def setUp(self):
        self.mocked_request_result = MockRequestResult()
        self.mocked_requests_get = MagicMock(return_value=self.mocked_request_result)
        requests.get = self.mocked_requests_get

        self.sample_msg_dict = {
            'args': (1, 2, 3),
            'kwargs': {'a': 'asdf', 'b': 123},
            'via': [
                ("service_name", (4, 5, 6), {'gfd': 123, 'ert': 908}),
                ("service_name2", (2, 6, 7), {'dfg': 123, 'wer': 908}),
            ],
            'results': {
                'service_name3': ('asdf', 345, 'yes')
            },
        }

        self.sample_message = communication.Message(**self.sample_msg_dict)

    def requests_get_has_pickled_calls(self, calls):
        self.assertEqual(len(self.mocked_requests_get.mock_calls), len(calls))

        for ii, cal in enumerate(calls):
            self.assertTrue('data' in self.mocked_requests_get.mock_calls[ii][2].keys())
            kwargs = self.mocked_requests_get.mock_calls[ii][2]
            data = kwargs.pop('data')

            self.assertEqual(cal[1][0], self.mocked_requests_get.mock_calls[ii][1][0])
            self.assertEqual(cal[1][1], pickle.loads(data))
            self.assertEqual(cal[2], kwargs)

    def test_send_to_uri(self):
        with self.subTest(msg="Test sending"):
            args = (5, 6, 7)
            kwargs = {
                'apple': "tasty",
                'banana': "loaf",
            }
            uri = "http://127.0.0.1:5000/test"

            communication.send_to_uri(__uri=uri, *args, **kwargs)

            expected_message = communication.Message.from_dict({
                'args': args,
                'kwargs': kwargs,
                'via': [],
                'results': {}
            })

            self.requests_get_has_pickled_calls([
                call(uri, expected_message)
            ])

        with self.subTest(msg="Test parsing response"):
            result = communication.send_to_uri(__uri=uri, *args, **kwargs)
            self.assertEqual(result, MockRequestResult().json()['args'])

    def test_Message(self):
        msg_dict = self.sample_msg_dict

        msg = communication.Message(**msg_dict)

        self.assertEqual(msg.via[0], communication.ViaHeader(*msg_dict['via'][0]))

        with self.subTest(msg="Test to and from dict"):
            self.assertEqual(msg_dict, msg.to_dict)
            self.assertEqual(msg, communication.Message.from_dict(msg_dict))

        with self.subTest(msg="Test pickle and unpickle"):
            pickled_unpickled = communication.Message.unpickle(msg.pickle)
            self.assertEqual(msg, pickled_unpickled)

    def test_send_message_to_service(self):
        service_name = "my_service-name"
        uri = communication.uri_from_service_name(service_name)
        with self.subTest(msg="Test parsing response"):
            result = communication.send_message_to_service(service_name, self.sample_message)
            self.requests_get_has_pickled_calls([
                call(uri, self.sample_message),
            ])
            self.assertEqual(result, MockRequestResult().json()['args'])

    def test_uri_from_service_name(self):
        service_name = "my_service-name"
        uri = communication.uri_from_service_name(service_name)
        self.assertEqual(uri, "http://my-service-name.pycroservices/")

        service_name = "really-long-really-long-really-long-really-long-really-long-really-long-really-long-really-long"
        uri = communication.uri_from_service_name(service_name)
        self.assertEqual(uri, "http://ng-really-long-really-long-really-long-really-long.pycroservices/")

    @patch('microservice.core.communication.send_message_to_service')
    def test_construct_and_send_call_to_service(self, mock_send_message_to_service: MagicMock):
        target_service = "my-service-name"
        local_service = "local-service"

        with self.subTest(msg="Test basic message creation"):
            args = self.sample_msg_dict['args']
            kwargs = self.sample_msg_dict['kwargs']  # type: dict
            communication.construct_and_send_call_to_service(
                target_service,
                local_service,
                communication.Message(results={'previous-service': (1, 5, 7)}),
                *args,
                **kwargs,
            )

            expected_result = communication.Message(**{
                'args': self.sample_msg_dict['args'],
                'kwargs': self.sample_msg_dict['kwargs'],
                'via': [communication.ViaHeader(local_service, tuple(), {})],
                'results': {'previous-service': (1, 5, 7)}
            })

            result_message = mock_send_message_to_service.call_args[0][1]
            mock_send_message_to_service.assert_called_once()
            self.assertEqual(mock_send_message_to_service.call_args[0][0], target_service)
            self.assertEqual(result_message, expected_result)

        mock_send_message_to_service.reset_mock()
        with self.subTest(msg="Test multiple vias"):
            communication.construct_and_send_call_to_service(
                target_service,
                local_service,
                result_message,
                *args,
                **kwargs,
            )

            expected_result.via.append(communication.ViaHeader(local_service, args, kwargs))

            result_message2 = mock_send_message_to_service.call_args[0][1]
            print(result_message2.to_dict)

            mock_send_message_to_service.assert_called_once()
            self.assertEqual(mock_send_message_to_service.call_args[0][0], target_service)
            self.assertEqual(result_message2, expected_result)
