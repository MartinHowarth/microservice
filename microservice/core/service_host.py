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


def add_local_service(service_name):
    print("Creating new service of name:", service_name)

    # Define the flask app route for this service.
    @app.route('/')
    def new_service():
        req_json = request.get_json()
        print("Service %s received request info:" % service_name, req_json)
        if req_json is None:
            req_json = {}
        func_args = req_json.get('_args', [])
        func_kwargs = req_json.get('_kwargs', {})
        result = settings.ServiceWaypost.locate(service_name)(*func_args, **func_kwargs)
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


def initialise_microservice(services, host="0.0.0.0", port="5000", **kwargs):
    from microservice.core.service_waypost import init_service_waypost
    init_service_waypost(**kwargs)
    for service in services:
        add_local_service(service)

    app.run(host=host, port=port, threaded=True)
