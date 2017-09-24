from microservice.core.service_waypost import _ServiceWaypost


class MockServiceWaypost(_ServiceWaypost):
    orchestrator_uri = "http://127.0.0.1:4999/orchestration"

    local_url = "http://127.0.0.1:5000"

    def locate_from_orchestrator(self, service_name):
        uri = "%s/%s" % (self.local_url, service_name)
        return uri
