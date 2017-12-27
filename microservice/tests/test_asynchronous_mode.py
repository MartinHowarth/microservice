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
        super(TestAsynchronousLocalService, cls).setUpClass()
        settings.deployment_mode = settings.Mode.ACTOR

        cls.args = (1, 2, 3)
        cls.kwargs = {'a': 'asdf', 'b': 123}

    def test_request(self):
        """
        Test that:
         - A 200 response is received to making a request to a microservice
         - A separate request is made back to the calling service with the result.
        """
        previous_service_name = "previous_service_name"
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict')

        test_msg = communication.construct_message_add_via(
            previous_service_name,
            communication.Message(
                results={
                    'other_service_name': [1, 3, 5, 7]
                },
                request_id=123456,
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
        self.mocked_send_object_to_service.assert_has_calls([
            call(previous_service_name,
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
                     },
                     'request_id': 123456,
                 })),
        ])

    def test_request_resulting_in_exception(self):
        """
        Test that:
         - A 200 response is received to making a request to a microservice
         - A separate request is made back to the calling service with the result, which is an exception
        """
        previous_service_name = "previous_service_name"
        self.mock_setup('microservice.tests.microservices_for_testing.exception_raiser')

        test_msg = communication.construct_message_add_via(
            previous_service_name,
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

        # Python in-built comparison for exceptions doesn't work for different instances, so
        # have to compare the arguments directly.
        self.mocked_send_object_to_service.assert_called_once()

        # Check the service name is as expected
        self.assertEqual(previous_service_name,
                         self.mocked_send_object_to_service.mock_calls[0][1][0])

        # Check that the details of the exception are as expected
        expected = RuntimeError("Called with: {}; {}".format(self.args, self.kwargs))
        actual = self.mocked_send_object_to_service.mock_calls[0][1][1]
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.args, actual.args)

    def test_request_with_originating_args(self):
        """
        Test that:
         - The call back to the originating microservice contains the args and kwargs that that microservice was
            originally called with
        """
        previous_service_name = 'previous_service_name'
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict')

        previous_service_args = [1, 2, 6]
        previous_service_kwargs = {
            3: 6,
            'asdf': 'wryt'
        }

        test_msg = communication.construct_message_add_via(
            previous_service_name,
            communication.Message(
                args=previous_service_args,
                kwargs=previous_service_kwargs,
                results={
                    'other_service_name': [1, 3, 5, 7]
                },
                request_id=123456
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
        self.mocked_send_object_to_service.assert_has_calls([
            call(previous_service_name,
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
                     },
                     'request_id': 123456,
                 })),
        ])

    def test_nested_request(self):
        nested_service_name = "microservice.tests.microservices_for_testing.echo_as_dict"
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict2')

        previous_service_args = (1, 2, 6)
        previous_service_kwargs = {
            3: 6,
            'asdf': 'wryt'
        }
        
        test_msg = communication.construct_message_add_via(
            "previous_service_name",
            communication.Message(
                args=previous_service_args,
                kwargs=previous_service_kwargs,
                results={
                    'other_service_name': [1, 3, 5, 7]
                },
                request_id=123456
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
        self.mocked_send_object_to_service.assert_has_calls([
            call(nested_service_name,
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
                     },
                     'request_id': 123456,
                 })),
            ])

    def test_nested_call_is_not_made_if_already_calculated(self):
        """
        The nested service result should be stored in the `results` dict of the call back to the original
        actor, and that should be used to save calling into the nested service again.
        """
        previous_service_name = 'previous_service_name'
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

        test_msg = communication.construct_message_add_via(
            previous_service_name,
            communication.Message(
                args=previous_service_args,
                kwargs=previous_service_kwargs,
                results={
                    'microservice.tests.microservices_for_testing.echo_as_dict': echo_as_dict_expected_result
                },
                request_id=123456
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

        self.mocked_send_object_to_service.assert_has_calls([
            call(previous_service_name,
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
                     },
                     'request_id': 123456,
                 })),
        ])
