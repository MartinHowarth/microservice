import requests

from unittest import TestCase

from microservice import initialise_interface, terminate_interface
from microservice.core import settings, deploy, microservice_logging

from microservice.tests.microservices_for_testing import (all_test_microservices, echo_as_dict, echo_as_dict2,
                                                          echo_as_dict2_args, echo_as_dict2_kwargs, exception_raiser)


class TestSubprocessDeployment(TestCase):
    deployment = None
    original_deployment_mode = settings.deployment_mode

    @classmethod
    def setUpClass(cls):
        microservice_logging.configure_logging("TEST")
        settings.deployment_mode = settings.DeploymentMode.SUBPROCESS

        initialise_interface()

        deploy.create_deployment(all_test_microservices)

    @classmethod
    def tearDownClass(cls):
        import time
        time.sleep(10)
        deploy.destroy_deployment()
        settings.deployment_mode = cls.original_deployment_mode

        terminate_interface()

    def test_echo(self):
        service_name = 'microservice.tests.microservices_for_testing.echo_as_dict'
        resp = requests.get(settings.ServiceWaypost.deployment.uri_for_service(service_name) + 'echo')
        self.assertEqual(resp.text, service_name)

    def test_ping(self):
        service_name = 'microservice.tests.microservices_for_testing.echo_as_dict'
        resp = requests.get(settings.ServiceWaypost.deployment.uri_for_service(service_name) + 'ping')
        self.assertEqual(resp.text, "pong")

    def test_microservice_request(self):
        args = (3, 4, 5, 'asdf')
        kwargs = {'sdfg': 2345, 'rteu': 'asfdg'}
        result = echo_as_dict(*args, **kwargs)

        self.assertEqual(result, {'_args': (3, 4, 5, 'asdf'), 'sdfg': 2345, 'rteu': 'asfdg'})

    def test_microservice_nested_request(self):
        args = (3, 4, 5, 'asdf')
        kwargs = {'sdfg': 2345, 'rteu': 'asfdg'}
        result = echo_as_dict2(*args, **kwargs)

        self.assertEqual(result, ({'_args': args, **kwargs},
                                  {'_args': echo_as_dict2_args, **echo_as_dict2_kwargs}))

    def test_exception_raiser(self):
        with self.assertRaises(RuntimeError):
            exception_raiser()
