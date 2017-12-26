import pickle
import requests

from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from microservice.core import communication
from microservice.tests.microservice_test_case import MicroserviceTestCase, MockRequestResult


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
            'request_id': 123456,
        }

        self.sample_message = communication.Message(**self.sample_msg_dict)

    def test_send_object_to_service(self):
        obj = self.sample_message
        service_name = "sample_service_name"
        expected_uri = communication.uri_from_service_name(service_name)

        result = communication.send_object_to_service(service_name, obj)
        print(communication.send_object_to_service)

        expected_object = communication.Message.from_dict(self.sample_msg_dict)

        with self.subTest(msg="Check requests is called as expected"):
            # We can't do a built-in comparison because the object is pickled before it is
            # sent. The result of a pickle is unique for different objects, even if their contents
            # are identical.
            self.mocked_requests_get.assert_called_once()

            self.assertTrue('data' in self.mocked_requests_get.mock_calls[0][2].keys())
            kwargs = self.mocked_requests_get.mock_calls[0][2]
            data = kwargs.pop('data')

            called_uri = self.mocked_requests_get.mock_calls[0][1][0]
            called_object = pickle.loads(data)

            self.assertEqual(expected_uri, called_uri)
            self.assertEqual(expected_object, called_object)

        with self.subTest(msg="Check response is parsed correctly"):
            self.assertEqual(MockRequestResult.args, result)

    def test_Message(self):
        msg_dict = self.sample_msg_dict

        msg = communication.Message(**msg_dict)

        self.assertEqual(msg.via[0], communication.ViaHeader(*msg_dict['via'][0]))

        with self.subTest(msg="Test to and from dict"):
            self.assertEqual(msg_dict, msg.to_dict)
            self.assertEqual(msg, communication.Message.from_dict(msg_dict))

        with self.subTest(msg="Test pickle and unpickle"):
            pickled = msg.pickle
            unpickled = communication.Message.unpickle(pickled)
            self.assertEqual(msg, unpickled)

    def test_uri_from_service_name(self):
        service_name = "my_service-name"
        uri = communication.uri_from_service_name(service_name)
        self.assertEqual(uri, "http://my-service-name.pycroservices/")

        service_name = "really-long-really-long-really-long-really-long-really-long-really-long-really-long-really-long"
        uri = communication.uri_from_service_name(service_name)
        self.assertEqual(uri, "http://ng-really-long-really-long-really-long-really-long.pycroservices/")

    @patch('microservice.core.communication.send_object_to_service')
    def test_construct_and_send_call_to_service(self, mock_send_object_to_service: MagicMock):
        target_service = "my-service-name"
        local_service = "local-service"

        with self.subTest(msg="Test basic message creation"):
            args = self.sample_msg_dict['args']
            kwargs = self.sample_msg_dict['kwargs']  # type: dict
            communication.construct_and_send_call_to_service(
                target_service,
                local_service,
                communication.Message(results={'previous-service': (1, 5, 7)}, request_id=123456),
                *args,
                **kwargs,
            )

            expected_result = communication.Message(**{
                'args': self.sample_msg_dict['args'],
                'kwargs': self.sample_msg_dict['kwargs'],
                'via': [communication.ViaHeader(local_service, tuple(), {})],
                'results': {'previous-service': (1, 5, 7)},
                'request_id': self.sample_msg_dict['request_id']
            })

            result_message = mock_send_object_to_service.call_args[0][1]
            mock_send_object_to_service.assert_called_once()
            self.assertEqual(mock_send_object_to_service.call_args[0][0], target_service)
            self.assertEqual(result_message, expected_result)

        mock_send_object_to_service.reset_mock()
        with self.subTest(msg="Test multiple vias"):
            communication.construct_and_send_call_to_service(
                target_service,
                local_service,
                result_message,
                *args,
                **kwargs,
            )

            expected_result.via.append(communication.ViaHeader(local_service, args, kwargs))

            result_message2 = mock_send_object_to_service.call_args[0][1]

            mock_send_object_to_service.assert_called_once()
            self.assertEqual(mock_send_object_to_service.call_args[0][0], target_service)
            self.assertEqual(result_message2, expected_result)
