from flask import Flask, request, jsonify

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
        if action in management_waypost.values():
            result = management_waypost[action](*args, **kwargs)
        else:
            raise InvalidUsage("The requested management action `%s` does not exist." % action)
    else:
        raise InvalidUsage("There was no json included in the management request.")
    return jsonify({'_args': result})


def add_service(service_name):
    print("Creating new service of name:", service_name)

    # Define the flask app route for this service.
    @app.route('/%s' % service_name, endpoint=service_name)
    def new_service():
        req_json = request.get_json()
        func_args = req_json.pop('_args')
        print("here")
        result = settings.local_waypost[service_name](*func_args, **req_json)
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
    settings.local_waypost.register_local_service(service_name, func)


management_waypost = {
    'add_service': add_service
}


def initialise_microservice(services):
    for service in services:
        add_service(service)

    app.run()
