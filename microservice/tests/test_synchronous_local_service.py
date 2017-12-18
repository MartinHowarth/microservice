import json
from unittest import TestCase

from microservice.core import settings, communication
from microservice.core.service_waypost import init_service_waypost

from microservice.core import service_host


class TestSynchronousLocalService(TestCase):
    @classmethod
    def setUpClass(cls):
        service_host.configure_microservice()
        init_service_waypost()
        settings.deployment_mode = settings.Mode.SYN

        service_host.app.testing = True
        cls.app = service_host.app.test_client()
        cls.service_name = "microservice.tests.microservices_for_testing.echo_as_dict"
        service_host.add_local_service(cls.service_name)

        cls.sample_msg_dict = {
            'args': (1, 2, 3),
            'kwargs': {'a': 'asdf', 'b': 123},
        }

        cls.sample_message = communication.Message.from_dict(cls.sample_msg_dict)

    def test_blank_request(self):
        response = self.app.get('/')
        result = json.loads(response.data.decode('utf-8'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(result.keys()) == 1)
        self.assertEqual(result['args'], {'_args': []})

    def test_request(self):
        response = self.app.get(
            '/',
            data=json.dumps(self.sample_message.to_dict),
            content_type='application/json')
        result = json.loads(response.data.decode('utf-8'))

        expected_result = {'args': {'_args': [1, 2, 3], 'a': 'asdf', 'b': 123}}
        print(result)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(result, expected_result)
