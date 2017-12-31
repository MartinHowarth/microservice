import pickle
import time

from microservice.tests.microservice_test_case import MicroserviceTestCase
from unittest.mock import call

from microservice.core import settings, communication

from microservice.tests import microservices_for_testing


class TestAsynchronousLocalService(MicroserviceTestCase):
    # Timer to allow the async threads to complete before we check their results.
    # It would be better to actually wait for the threads to complete, but this is far simpler.
    THREAD_TIMER = 0.1

    @classmethod
    def setUpClass(cls):
        super(TestAsynchronousLocalService, cls).setUpClass()
        settings.communication_mode = settings.CommunicationMode.ACTOR
        settings.deployment_mode = settings.DeploymentMode.KUBERNETES
        settings.local_uri = None

        cls.args = (1, 2, 3)
        cls.kwargs = {'a': 'asdf', 'b': 123}

    def test_request(self):
        """
        Test that:
         - A 200 response is received to making a request to a microservice
         - A separate request is made back to the calling service with the result.
        """
        local_service_name = 'microservice.tests.microservices_for_testing.echo_as_dict'
        self.mock_setup(local_service_name)

        orig_msg = communication.Message()
        orig_msg.add_result('other_service_name', (), {}, [1, 3, 5, 7])
        test_msg = communication.construct_message_add_via(
            orig_msg,
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

        expected_message = communication.Message()
        expected_message.add_result('other_service_name', (), {}, [1, 3, 5, 7])
        expected_message.add_result(local_service_name, self.args, self.kwargs, {
            '_args': tuple(self.args),
            **self.kwargs
        })
        self.mocked_send_object_to_service.assert_has_calls([
            call(local_service_name,
                 expected_message),
        ])

    def test_request_resulting_in_exception(self):
        """
        Test that:
         - A 200 response is received to making a request to a microservice
         - A separate request is made back to the calling service with the result, which is an exception
        """
        local_service_name = 'microservice.tests.microservices_for_testing.exception_raiser'
        self.mock_setup(local_service_name)

        test_msg = communication.construct_message_add_via(
            communication.Message(),
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
        self.assertEqual(local_service_name,
                         self.mocked_send_object_to_service.mock_calls[0][1][0])

        # Check that the details of the exception are as expected
        expected = RuntimeError("Called with: {}; {}".format(self.args, self.kwargs))
        result_message = self.mocked_send_object_to_service.mock_calls[0][1][1]
        actual = result_message.get_result(local_service_name, self.args, self.kwargs)
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.args, actual.args)

    def test_request_with_originating_args(self):
        """
        Test that:
         - The call back to the originating microservice contains the args and kwargs that that microservice was
            originally called with
        """
        local_service_name = 'microservice.tests.microservices_for_testing.echo_as_dict'
        self.mock_setup(local_service_name)

        previous_service_args = [1, 2, 6]
        previous_service_kwargs = {
            3: 6,
            'asdf': 'wryt'
        }

        test_msg = communication.construct_message_add_via(
            communication.Message(
                args=previous_service_args,
                kwargs=previous_service_kwargs,
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

        expected_message = communication.Message.from_dict({
            'args': previous_service_args,
            'kwargs': previous_service_kwargs,
        })
        expected_message.add_result(local_service_name, self.args, self.kwargs, {
            '_args': tuple(self.args),
            **self.kwargs
        })

        self.mocked_send_object_to_service.assert_has_calls([
            call(local_service_name,
                 expected_message),
        ])

    def test_nested_request(self):
        nested_service_name = "microservice.tests.microservices_for_testing.echo_as_dict"
        local_service_name = 'microservice.tests.microservices_for_testing.echo_as_dict2'
        self.mock_setup(local_service_name)

        previous_service_args = (1, 2, 6)
        previous_service_kwargs = {
            3: 6,
            'asdf': 'wryt'
        }

        test_msg = communication.construct_message_add_via(
            communication.Message(
                args=previous_service_args,
                kwargs=previous_service_kwargs,
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

        expected_message = communication.Message.from_dict({
            'args': (5, 2, 5),
            'kwargs': {'asdf': 'asdrf'},
            'via': [
                (local_service_name,
                 previous_service_args,
                 previous_service_kwargs),
                ('microservice.tests.microservices_for_testing.echo_as_dict2',
                 self.args,
                 self.kwargs)
            ],
        })

        self.mocked_send_object_to_service.assert_has_calls([
            call(nested_service_name,
                 expected_message),
        ])

    def test_nested_call_is_not_made_if_already_calculated(self):
        """
        The nested service result should be stored in the `results` dict of the call back to the original
        actor, and that should be used to save calling into the nested service again.
        """
        local_service_name = 'microservice.tests.microservices_for_testing.echo_as_dict2'
        self.mock_setup(local_service_name)

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
            communication.Message(
                args=previous_service_args,
                kwargs=previous_service_kwargs,
            ),
            *self.args,
            **self.kwargs,
        )
        test_msg.add_result('microservice.tests.microservices_for_testing.echo_as_dict',
                            microservices_for_testing.echo_as_dict2_args,
                            microservices_for_testing.echo_as_dict2_kwargs,
                            echo_as_dict_expected_result)

        response = self.app.get(
            '/',
            data=test_msg.pickle,
            content_type='application/json')
        result = pickle.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, True)
        # Wait for the thread pool to complete the work.
        time.sleep(self.THREAD_TIMER)

        expected_message = communication.Message.from_dict({
            'args': previous_service_args,
            'kwargs': previous_service_kwargs,
        })
        expected_message.add_result('microservice.tests.microservices_for_testing.echo_as_dict',
                                    microservices_for_testing.echo_as_dict2_args,
                                    microservices_for_testing.echo_as_dict2_kwargs,
                                    echo_as_dict_expected_result)
        expected_message.add_result('microservice.tests.microservices_for_testing.echo_as_dict2',
                                    self.args,
                                    self.kwargs,
                                    (
                                        {
                                            '_args': self.args,
                                            **self.kwargs
                                        },
                                        echo_as_dict_expected_result,
                                    ))
        self.mocked_send_object_to_service.assert_has_calls([
            call(local_service_name,
                 expected_message),
        ])

    def test_interface_request(self):
        """
        Test that calling into a decorated function with only args/kwargs results in a call to the relevant
        microservice.
        """
        self.mock_setup('my_app', interface=True)

        args = (3, 4, 5)
        kwargs = {'erty': 5, 'asdf': 'asddfg'}
        expected_result = ("nonsense", 35)
        target_service_name = 'microservice.tests.microservices_for_testing.echo_as_dict'
        result_key = communication.create_result_key(target_service_name, args, kwargs)

        # Make the result for this request available to pretend that it's been carried out successfully.
        settings.set_interface_result(self.request_id, expected_result)

        result = microservices_for_testing.echo_as_dict(*args, **kwargs)

        # Make sure that we've flagged this request ID as being made
        self.assertIn(self.request_id, settings.interface_requests.keys())
        self.assertEqual(result_key, settings.interface_requests[self.request_id])

        self.assertEqual(result, expected_result)
        self.mocked_send_object_to_service.assert_has_calls([
            call(target_service_name,
                 communication.Message.from_dict({
                     'args': args,
                     'kwargs': kwargs,
                     'via': [('my_app', (), {})],
                     'request_id': self.request_id,
                 })),
        ])

    def test_interface_response(self):
        """
        This test covers the handling of a response to a request made from an interface.
        It relies on the results being handled (and cached) separately to the request being made. It does:
            - Set up the local microservice handler in interface mode.
            - Send the response to this local handler (flask app)
            - Ensure that response is stored correctly
            - Make a request that would wait for that response, but finishes immediately because it's already available.

        The reason for doing this back to front (response, then request) is to avoid complicating the test with
        threading (as the request blocks until the response is received).
        """
        self.mock_setup('my_app', interface=True)

        args = (3, 4, 5)
        kwargs = {'erty': 5, 'asdf': 'asddfg'}
        expected_result = ("nonsense", 35)

        target_service_name = 'microservice.tests.microservices_for_testing.echo_as_dict'
        result_key = communication.create_result_key(target_service_name, args, kwargs)

        # State that we're expecting a response for a request matching self.request_id
        settings.set_interface_request(self.request_id, result_key)

        # Construct the message that we'd expect to see back in response
        response_message = communication.Message(
            request_id=self.request_id,
        )
        response_message.add_result(target_service_name, args, kwargs, expected_result)

        # Send the response - the answer should get placed in the response storage.
        response = self.app.get(
            '/',
            data=response_message.pickle,
            content_type='application/json')
        response_result = pickle.loads(response.data)

        self.assertEqual(response_result, True)

        # Wait for the thread pool to complete the work.
        time.sleep(self.THREAD_TIMER)

        # Check that the result has been logged
        self.assertIn(self.request_id, settings.interface_results.keys())
        self.assertEqual(expected_result, settings.interface_results[self.request_id])

        # Make the request that this corresponds to, to check that the result is picked up correctly.
        result = microservices_for_testing.echo_as_dict(*args, **kwargs)

        self.assertEqual(result, expected_result)

        # Remove the hanging request id to tidy up for any other tests.
        # This is only required because we're doing this test in the reverse order (response, then request).
        del settings.interface_requests[self.request_id]

    def test_interface_response_resulting_in_exception(self):
        """
        This test is identical to the test `test_interface_response`, but the response is an exception, so we expect
        to see it raised instead of simply returned.
        """
        self.mock_setup('my_app', interface=True)

        args = (3, 4, 5)
        kwargs = {'erty': 5, 'asdf': 'asddfg'}
        expected_result = RuntimeError("Sample error that should get raised.")

        target_service_name = 'microservice.tests.microservices_for_testing.echo_as_dict'
        result_key = communication.create_result_key(target_service_name, args, kwargs)

        # State that we're expecting a response for a request matching self.request_id
        settings.set_interface_request(self.request_id, result_key)

        # Construct the message that we'd expect to see back in response
        response_message = communication.Message(
            request_id=self.request_id,
        )
        response_message.add_result(target_service_name, args, kwargs, expected_result)

        # Send the response - the answer should get placed in the response storage.
        response = self.app.get(
            '/',
            data=response_message.pickle,
            content_type='application/json')
        response_result = pickle.loads(response.data)

        self.assertEqual(response_result, True)

        # Wait for the thread pool to complete the work.
        time.sleep(self.THREAD_TIMER)

        # Make the request that this corresponds to, to check that the result is picked up correctly.
        with self.assertRaises(type(expected_result)):
            microservices_for_testing.echo_as_dict(*args, **kwargs)

        # Remove the hanging request id to tidy up for any other tests.
        # This is only required because we're doing this test in the reverse order (response, then request).
        del settings.interface_requests[self.request_id]
