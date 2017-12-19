import json
from unittest import TestCase

from microservice.core import settings, communication
from microservice.core.service_waypost import init_service_waypost

from microservice.core import service_host


class TestSynchronousLocalService(TestCase):
    def setUp(self):
        settings.deployment_mode = settings.Mode.SYN

        self.sample_msg_dict = {
            'args': (1, 2, 3),
            'kwargs': {'a': 'asdf', 'b': 123},
        }

        self.sample_message = communication.Message.from_dict(self.sample_msg_dict)

    def mock_setup(self, service_name):
        service_host.configure_microservice()
        init_service_waypost()

        service_host.app.testing = True
        self.app = service_host.app.test_client()
        self.service_name = service_name
        service_host.add_local_service(self.service_name)

    def test_blank_request(self):
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict')

        response = self.app.get('/')
        result = json.loads(response.data.decode('utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(result.keys()) == 1)
        self.assertEqual(result['args'], {'_args': []})

    def test_request(self):
        self.mock_setup('microservice.tests.microservices_for_testing.echo_as_dict')

        response = self.app.get(
            '/',
            data=json.dumps(self.sample_message.to_dict),
            content_type='application/json')
        result = json.loads(response.data.decode('utf-8'))

        expected_result = {'args': {'_args': [1, 2, 3], 'a': 'asdf', 'b': 123}}
        print(result)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, expected_result)
