from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify

from microservice.core import settings, communication


def configure_microservice():
    """
    Configure the flask app. If this is called a second time, it tears down the existing app and re-creates it.
    """
    global app, executor
    app = Flask(__name__)
    if settings.deployment_mode == settings.Mode.ACTOR:
        executor = ThreadPoolExecutor(max_workers=5)


app = None  # type: Flask
executor = None  # type: ThreadPoolExecutor
configure_microservice()


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


def perform_service(message: communication.Message):
    # Actually carry out the service.
    try:
        print("Calling local function")
        # Make the current message available globally
        # Note that this uses `threading.local()` to ensure that this message is only available to the current thread.
        settings.current_message = message
        result = settings.ServiceWaypost.local_function(*message.args, **message.kwargs)
        print("Result is: {}".format(result))
    except communication.ServiceCallPerformed as e:
        print(e)
        # TODO: return the exception to the calling microservice
        raise e
        return

    # Send message back to calling party (which is the last via header)
    print("original message is: {}".format(message.to_dict))
    return_service = message.via[-1].service_name
    return_args = message.via[-1].args
    return_kwargs = message.via[-1].kwargs
    message.results.update({
            settings.ServiceWaypost.local_service: result
        })
    return_message = communication.Message(
        args=return_args,
        kwargs=return_kwargs,
        via=message.via[:-1],
        results=message.results,
    )
    print("Return message is: {}".format(return_message.to_dict))
    print("Return service is: {}".format(return_service))
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

        if settings.deployment_mode == settings.Mode.SYN:
            result = settings.ServiceWaypost.local_function(__message=msg)
            return jsonify({'args': result})
        elif settings.deployment_mode == settings.Mode.ACTOR:
            # Kick off the process to do the work and send the response.
            print("Submitting work to executor")
            executor.submit(perform_service, msg)

            print("Work has been scheduled")
            # Ack the request.
            return jsonify(True)
        raise ValueError("Invalid deployment mode: {}".format(settings.deployment_mode))

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
    configure_microservice()
    init_service_waypost()
    add_local_service(service_name)

    app.run(host=host, port=port, threaded=True)
