from flask import Flask, request, jsonify


from microservice.core.decorator import robust_service_call
from microservice.core.health_checker import HealthChecker
from microservice.core import settings

app = Flask(__name__)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route("/__management")
def management():
    """
    General interface for the external forces to manage this microservice.

    This is the interface that the Orchestrator uses.
    """
    management_json = request.get_json()
    if management_json:
        print("Received management request:", management_json)
        action = management_json.get('action', None)
        args = management_json.get('_args', [])
        kwargs = management_json.get('_kwargs', {})
        if action in management_waypost.keys():
            result = management_waypost[action](*args, **kwargs)
        else:
            if action.startswith('__TEST__'):
                # Expose all functions so they can be triggered by a test function.
                target, func = action[len('__TEST__'):].split('.')
                result = test_override(target, func, *args, **kwargs)
            raise InvalidUsage("The requested management action `%s` does not exist." % action)
    else:
        raise InvalidUsage("There was no json included in the management request.")
    return jsonify({'_args': result})


def add_local_service(service_name):
    print("Creating new service of name:", service_name)

    # Define the flask app route for this service.
    @app.route('/%s' % service_name, endpoint=service_name)
    def new_service():
        req_json = request.get_json()
        print("Service %s received request info:" % service_name, req_json)
        if req_json is None:
            req_json = {}
        func_args = req_json.get('_args', [])
        func_kwargs = req_json.get('_kwargs', {})
        result = robust_service_call(service_name)(*func_args, **func_kwargs)
        return jsonify({'_args': result})

    # Now expose this function at the global scope so that it persists as a new flask route.
    new_service.name = service_name
    globals()[service_name] = new_service
    print("Created new service:", new_service)

    # Finally register this service with the local ServiceWaypost.
    func_name = service_name.split('.')[-1]
    mod_name = '.'.join(service_name.split('.')[:-1])
    mod = __import__(mod_name, globals(), locals(), [func_name], 0)
    func = getattr(mod, func_name)
    print("Dynamically found module is:", mod)
    print("Dynamically found function is:", func)
    settings.ServiceWaypost.register_local_service(service_name, func)


def receive_service_advertisement(service_name, service_uri):
    settings.ServiceWaypost.add_service_provider(service_name, service_uri)


def receive_service_retirement(service_name, service_uri):
    settings.ServiceWaypost.remove_service_provider(service_name, service_uri)


def receive_orchestrator_info(orchestrator_uri, local_uri):
    print("Orchestrator is found at:", orchestrator_uri)
    settings.ServiceWaypost.orchestrator_uri = orchestrator_uri
    settings.ServiceWaypost.local_uri = local_uri


def current_deployment_information():
    return settings.ServiceWaypost.current_deployment_information()


def heartbeat():
    return HealthChecker.heartbeat_info


def shut_down(quiesce=True):
    # Quiesce is always true with this implementation.
    def shutdown_server():
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
    shutdown_server()
    print("Shutting down server!!!")


def test_override(target, func, *args, **kwargs):
    """
    Generic interface to allow any function to be called. Primarily aimed for make this solution testable.
    :param target:
    :param func:
    :param args:
    :param kwargs:
    :return:
    """
    target_func = getattr(globals()[target], func)
    if callable(target_func):
        return target_func(*args, **kwargs)
    else:
        setattr(globals()[target], func, args[0])
        return args[0]


management_waypost = {
    'add_local_service': add_local_service,
    'receive_service_advertisement': receive_service_advertisement,
    'receive_service_retirement': receive_service_retirement,
    'receive_orchestrator_info': receive_orchestrator_info,
    'heartbeat': heartbeat,
    'shut_down': shut_down,
    'current_deployment_information': current_deployment_information,
}


def initialise_microservice(services, host="127.0.0.1", port="5000", **kwargs):
    from microservice.core.service_waypost import init_service_waypost
    init_service_waypost(**kwargs)
    for service in services:
        add_local_service(service)

    app.run(host=host, port=port, threaded=True)
