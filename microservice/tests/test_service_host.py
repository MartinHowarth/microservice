from unittest import TestCase

from microservice.core import settings
from microservice.core.service_waypost import init_service_waypost

from microservice.core import service_host


class TestServiceHost(TestCase):
    def setUp(self):
        init_service_waypost()
        settings.deployment_type = settings.DeploymentType.ZERO

    def test_test_override(self):
        self.assertEqual(service_host.HealthChecker.heartbeat_info, {
            'percent_idle': 1,
        })
        service_host.test_override("HealthChecker", '_override_heartbeat_response', {
            'percent_idle': 0.5,
        })
        self.assertEqual(service_host.HealthChecker.heartbeat_info, {
            'percent_idle': 0.5,
        })
