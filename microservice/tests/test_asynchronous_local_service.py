import pickle
import requests
import time

from unittest.mock import MagicMock, call, patch
from unittest import TestCase

from microservice.core import settings, communication
from microservice.core.service_waypost import init_service_waypost

from microservice.core import service_host

from microservice.tests import microservices_for_testing


class MockRequestResult(MagicMock):
    _json_args = (2, 3, 4)

    def json(self):
        return {
            'args': self._json_args
        }

    @property
    def content(self):
        return pickle.dumps(self._json_args)


class TestAsynchronousLocalService(TestCase):
    THREAD_TIMER = 0.1

    @classmethod
    def setUpClass(cls):
        settings.deployment_mode = settings.Mode.ACTOR

        cls.args = (1, 2, 3)
        cls.kwargs = {'a': 'asdf', 'b': 123}

    def mock_setup(self, service_name):
        service_host.configure_microservice()
        init_service_waypost()

        self.mocked_request_result = MockRequestResult()
        self.mocked_requests_get = MagicMock(return_value=self.mocked_request_result)
        requests.get = self.mocked_requests_get

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
            expected_message = cal[1][1]
            called_uri = self.mocked_requests_get.mock_calls[ii][1][0]
            called_message = pickle.loads(data)

            self.assertEqual(expected_uri, called_uri)
            self.assertEqual(expected_message, called_message)
            self.assertEqual(cal[2], kwargs)

    def test_request(self):
        """
        Test that:
         - A 200 response is received to making a request to a microservice
         - A separate request is made back to the calling service with the result.
        """
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict')

        test_msg = communication.construct_message(
            "previous_service_name",
            communication.Message(
                results={
                    'other_service_name': [1, 3, 5, 7]
                }
            ),
            *self.args,
            **self.kwargs,
        )

        response = self.app.get(
            '/',
            data=test_msg.pickle,
            content_type='application/json')
        result = pickle.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, True)
        # Wait for the thread pool to complete the work.
        time.sleep(self.THREAD_TIMER)
        self.requests_get_has_pickled_calls([
            call('http://previous-service-name.pycroservices/',
                 communication.Message.from_dict({
                     'args': (),
                     'kwargs': {},
                     'via': [],
                     'results': {
                         'other_service_name': [1, 3, 5, 7],
                         'microservice.tests.microservices_for_testing.echo_as_dict': {
                             '_args': tuple(self.args),
                             **self.kwargs
                         }
                     }
                 })),
        ])

    def test_request_with_originating_args(self):
        """
        Test that:
         - The call back to the originating microservice contains the args and kwargs that that microservice was
            originally called with
        """
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict')

        previous_service_args = [1, 2, 6]
        previous_service_kwargs = {
            3: 6,
            'asdf': 'wryt'
        }

        test_msg = communication.construct_message(
            "previous_service_name",
            communication.Message(
                args=previous_service_args,
                kwargs=previous_service_kwargs,
                results={
                    'other_service_name': [1, 3, 5, 7]
                }
            ),
            *self.args,
            **self.kwargs,
        )

        response = self.app.get(
            '/',
            data=test_msg.pickle,
            content_type='application/json')
        result = pickle.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, True)
        # Wait for the thread pool to complete the work.
        time.sleep(self.THREAD_TIMER)
        self.requests_get_has_pickled_calls([
            call('http://previous-service-name.pycroservices/',
                 communication.Message.from_dict({
                     'args': previous_service_args,
                     'kwargs': previous_service_kwargs,
                     'via': [],
                     'results': {
                         'other_service_name': [1, 3, 5, 7],
                         'microservice.tests.microservices_for_testing.echo_as_dict': {
                             '_args': tuple(self.args),
                             **self.kwargs
                         }
                     }
                 })),
        ])

    def test_nested_request(self):
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict2')

        previous_service_args = (1, 2, 6)
        previous_service_kwargs = {
            3: 6,
            'asdf': 'wryt'
        }
        
        test_msg = communication.construct_message(
            "previous_service_name",
            communication.Message(
                args=previous_service_args,
                kwargs=previous_service_kwargs,
                results={
                    'other_service_name': [1, 3, 5, 7]
                }
            ),
            *self.args,
            **self.kwargs,
        )
        response = self.app.get(
            '/',
            data=test_msg.pickle,
            content_type='application/json')
        result = pickle.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, True)
        # Wait for the thread pool to complete the work.
        time.sleep(self.THREAD_TIMER)
        self.requests_get_has_pickled_calls([
            call('http://rvice-tests-microservices-for-testing-echo-as-dict.pycroservices/',
                 communication.Message.from_dict({
                     'args': (5, 2, 5),
                     'kwargs': {'asdf': 'asdrf'},
                     'via': [
                         ('previous_service_name',
                          previous_service_args,
                          previous_service_kwargs),
                         ('microservice.tests.microservices_for_testing.echo_as_dict2',
                          self.args,
                          self.kwargs)
                     ],
                     'results': {
                        'other_service_name': [1, 3, 5, 7]
                     }
                 })),
            ])

    def test_nested_call_is_not_made_if_already_calculated(self):
        """
        The nested service result should be stored in the `results` dict of the call back to the original
        actor, and that should be used to save calling into the nested service again.
        """
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict2')

        previous_service_args = [1, 2, 6]
        previous_service_kwargs = {
            3: 6,
            'asdf': 'wryt'
        }

        echo_as_dict_expected_result = {
            '_args': microservices_for_testing.echo_as_dict2_args,
            **microservices_for_testing.echo_as_dict2_kwargs
        }

        test_msg = communication.construct_message(
            "previous_service_name",
            communication.Message(
                args=previous_service_args,
                kwargs=previous_service_kwargs,
                results={
                    'microservice.tests.microservices_for_testing.echo_as_dict': echo_as_dict_expected_result
                }
            ),
            *self.args,
            **self.kwargs,
        )

        response = self.app.get(
            '/',
            data=test_msg.pickle,
            content_type='application/json')
        result = pickle.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, True)
        # Wait for the thread pool to complete the work.
        time.sleep(self.THREAD_TIMER)

        self.requests_get_has_pickled_calls([
            call('http://previous-service-name.pycroservices/',
                 communication.Message.from_dict({
                     'args': previous_service_args,
                     'kwargs': previous_service_kwargs,
                     'via': [],
                     'results': {
                        'microservice.tests.microservices_for_testing.echo_as_dict': echo_as_dict_expected_result,
                        'microservice.tests.microservices_for_testing.echo_as_dict2': (
                            {
                                '_args': self.args,
                                **self.kwargs
                            },
                            echo_as_dict_expected_result,
                        )
                     }
                 })),
        ])
