import pickle

from unittest.mock import call

from microservice.tests.microservice_test_case import MicroserviceTestCase, MockRequestResult
from microservice.core import settings, communication

from microservice.tests import microservices_for_testing


class TestSynchronousLocalService(MicroserviceTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestSynchronousLocalService, cls).setUpClass()
        settings.communication_mode = settings.CommunicationMode.SYN
        settings.deployment_mode = settings.DeploymentMode.KUBERNETES
        settings.local_uri = None

        cls.sample_msg_dict = {
            'args': (1, 2, 3),
            'kwargs': {'a': 'asdf', 'b': 123},
            'request_id': 123456,
        }

        cls.sample_message = communication.Message.from_dict(cls.sample_msg_dict)

    def test_blank_request(self):
        local_service_name = 'microservice.tests.microservices_for_testing.echo_as_dict'
        self.mock_setup(local_service_name)

        response = self.app.get('/')
        result = pickle.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, communication.Message(
            results={local_service_name: {'_args': tuple()}}
        ))

    def test_request(self):
        local_service_name = 'microservice.tests.microservices_for_testing.echo_as_dict'
        self.mock_setup(local_service_name)

        response = self.app.get(
            '/',
            data=self.sample_message.pickle,
            content_type='application/json')
        result = pickle.loads(response.data)

        expected_result = communication.Message(
            results={local_service_name: {'_args': (1, 2, 3), 'a': 'asdf', 'b': 123}}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, expected_result)

    def test_nested_request(self):
        service_name = 'microservice.tests.microservices_for_testing.echo_as_dict2'
        nested_service_name = 'microservice.tests.microservices_for_testing.echo_as_dict'
        self.mock_setup(service_name)

        response = self.app.get(
            '/',
            data=self.sample_message.pickle,
            content_type='application/json')
        result = pickle.loads(response.data)

        expected_call = communication.Message(**{
            'via': [('microservice.tests.microservices_for_testing.echo_as_dict2', (1, 2, 3), {'a': 'asdf', 'b': 123})],
            'args': microservices_for_testing.echo_as_dict2_args,
            'kwargs': microservices_for_testing.echo_as_dict2_kwargs,
            'request_id': 123456,
        })
        expected_result = communication.Message(
            results={
                service_name: ({'_args': self.sample_message.args, **self.sample_message.kwargs},
                               MockRequestResult.args)
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(expected_result, result)

        self.mocked_send_object_to_service.assert_has_calls([
            call(nested_service_name,
                 expected_call)
        ])

    def test_exception_raised(self):
        local_service_name = 'microservice.tests.microservices_for_testing.exception_raiser'
        self.mock_setup(local_service_name)

        response = self.app.get(
            '/',
            data=self.sample_message.pickle,
            content_type='application/json')
        result_message = pickle.loads(response.data)

        expected = RuntimeError("Called with: {}; {}".format(self.sample_message.args, self.sample_message.kwargs))
        actual = result_message.results[local_service_name]
        self.assertEqual(type(expected), type(actual))
        self.assertEqual(expected.args, actual.args)
