from microservice.tests.microservice_test_case import MicroserviceTestCase
from microservice.core import settings

from microservice.tests import microservices_for_testing


class TestZeroMode(MicroserviceTestCase):
    @classmethod
    def setUpClass(cls):
        settings.deployment_mode = settings.Mode.ZERO
        cls.args = (1, 2, 3)
        cls.kwargs = {'a': 'asdf', 'b': 123}

    def test_basic_request(self):
        result = microservices_for_testing.echo_as_dict(
            *self.args,
            **self.kwargs
        )
        self.assertEqual(result, {'_args': self.args, **self.kwargs})
        self.mocked_requests_get.assert_has_calls([])

    def test_nested_request(self):
        result = microservices_for_testing.echo_as_dict2(
            *self.args,
            **self.kwargs
        )

        expected_result = (
            {'_args': self.args, **self.kwargs},
            {'_args': microservices_for_testing.echo_as_dict2_args,
             **microservices_for_testing.echo_as_dict2_kwargs}
        )

        self.assertEqual(result, expected_result)
        self.mocked_requests_get.assert_has_calls([])
