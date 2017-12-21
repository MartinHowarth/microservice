import pickle
import time

from microservice.tests.microservice_test_case import MicroserviceTestCase
from unittest.mock import call

from microservice.core import settings, communication

from microservice.tests import microservices_for_testing


class TestAsynchronousLocalService(MicroserviceTestCase):
    THREAD_TIMER = 0.1

    @classmethod
    def setUpClass(cls):
        settings.deployment_mode = settings.Mode.ACTOR

        cls.args = (1, 2, 3)
        cls.kwargs = {'a': 'asdf', 'b': 123}

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

    def test_request_resulting_in_exception(self):
        """
        Test that:
         - A 200 response is received to making a request to a microservice
         - A separate request is made back to the calling service with the result, which is an exception
        """
        self.mock_setup('microservice.tests.microservices_for_testing.exception_raiser')

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
                 RuntimeError("Called with: {}; {}".format(self.args, self.kwargs)))
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
