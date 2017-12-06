from microservice.core import settings


class _ServiceWaypost:
    local_uri = None

    service_functions = dict()

    local_service = None
    local_function = None

    local_services = []

    current_message = None


def init_service_waypost():
    settings.ServiceWaypost = _ServiceWaypost()
