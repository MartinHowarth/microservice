from celery import Celery
from flask import Flask, request, jsonify

from microservice.core import settings, communication

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'redis://0.0.0.0:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://0.0.0.0:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


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


@celery.task
def perform_service():
    message = settings.ServiceWaypost.current_message
    # Actually carry out the service.
    try:
        result = settings.ServiceWaypost.local_function(*message.args, **message.kwargs)
    except communication.ServiceCallPerformed as e:
        print(e)
        return

    # Send message back to calling party (which should be the last via header)
    return_service = message.via[-1].service_name
    return_args = message.via[-1].args
    return_kwargs = message.via[-1].kwargs
    return_message = communication.Message(
        args=return_args,
        kwargs=return_kwargs,
        via=message.via[:-1],
        results=message.results.update({
            return_service: result
        }),
    )
    communication.send_message_to_service(return_service, return_message)


def add_local_service(service_name):
    print("Creating new service of name:", service_name)

    # Define the flask app route for this service.
    @app.route('/')
    def new_service():
        req_json = request.get_json()
        print("Service %s received request info:" % service_name, req_json)
        if req_json is None:
            req_json = {}

        msg = communication.Message.from_dict(req_json)
        settings.ServiceWaypost.current_message = msg

        if settings.deployment_mode == settings.Mode.SYN:
            result = settings.ServiceWaypost.local_function(__message=msg)
            return jsonify({'args': result})
        elif settings.deployment_mode == settings.Mode.ACTOR:
            # Kick off the process to do the work and send the response.
            perform_service.delay()

            # Ack the request.
            return True

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
    settings.ServiceWaypost.local_service = service_name
    settings.ServiceWaypost.local_function = func


def initialise_microservice(service_name, host="0.0.0.0", port="5000", **kwargs):
    from microservice.core.service_waypost import init_service_waypost
    init_service_waypost()
    add_local_service(service_name)

    app.run(host=host, port=port, threaded=True)
