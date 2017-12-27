import pickle

from unittest.mock import call

from microservice.tests.microservice_test_case import MicroserviceTestCase, MockRequestResult
from microservice.core import settings, communication

from microservice.tests import microservices_for_testing


class TestSynchronousLocalService(MicroserviceTestCase):
    @classmethod
    def setUpClass(cls):
        super(TestSynchronousLocalService, cls).setUpClass()
        settings.deployment_mode = settings.Mode.SYN

        cls.sample_msg_dict = {
            'args': (1, 2, 3),
            'kwargs': {'a': 'asdf', 'b': 123},
            'request_id': 123456,
        }

        cls.sample_message = communication.Message.from_dict(cls.sample_msg_dict)

    def test_blank_request(self):
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict')

        response = self.app.get('/')
        result = pickle.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, {'_args': ()})

    def test_request(self):
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict')

        response = self.app.get(
            '/',
            data=self.sample_message.pickle,
            content_type='application/json')
        result = pickle.loads(response.data)

        expected_result = {'_args': (1, 2, 3), 'a': 'asdf', 'b': 123}
        print(result)

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
        expected_result = ({'_args': self.sample_message.args, **self.sample_message.kwargs},
                           MockRequestResult.args)
        print("result is", result)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(expected_result, result)

        self.mocked_send_object_to_service.assert_has_calls([
            call(nested_service_name,
                 expected_call)
        ])
