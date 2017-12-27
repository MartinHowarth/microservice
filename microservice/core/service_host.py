import flask
import logging
import pickle

from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, g

from microservice.core import settings, communication

logger = logging.getLogger(__name__)


def configure_microservice():
    """
    Configure the flask app. If this is called a second time, it tears down the existing app and re-creates it.
    """
    global app, executor
    app = Flask(__name__)
    if settings.deployment_mode == settings.Mode.ACTOR:
        executor = ThreadPoolExecutor(max_workers=5)

    logger.info("Microservice configured")


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
    return_service = message.via[-1].service_name

    # Make the current message available globally
    # Note that this uses `threading.local()` to ensure that this message is only available to the current thread.
    settings.thread_locals.current_message = message
    logger.debug("Original message is: {microservice_message}", extra={'microservice_message': message})

    # Actually carry out the service.
    try:
        logger.debug("Calling local function")
        result = settings.ServiceWaypost.local_function(*message.args, **message.kwargs)
        logger.debug("Result is: {result}", extra={'result': result})
    except communication.ServiceCallPerformed as e:
        logger.info("Nested service call complete: {nested_service}", extra={'nested_service', str(e)})
    except Exception as err:
        logger.exception("Unexpected exception: {err}", exc_info=True, stack_info=True,  extra={'err': err})
        communication.send_object_to_service(return_service, err)
    else:
        logger.info("No more nested microservices, starting return.")
        # Send message back to calling party (which is the last via header)
        return_message = communication.construct_message_with_result(message, result)
        logger.debug("Return message is: {microservice_message}", extra={'microservice_message': message})
        logger.info("Return service is: {return_service}", extra={'return_service': return_service})
        communication.send_object_to_service(return_service, return_message)
    finally:
        settings.thread_locals.current_message = None


def add_local_service(service_name):
    logger.info("Adding local service of name: {service_name}", extra={'service_name': service_name})

    # Define the flask app route for this service.
    @app.route('/')
    def new_service():
        logger.info("Service {service_name} received request", extra={'service_name': service_name})
        if request.data:
            msg = pickle.loads(request.data)
        else:
            msg = communication.Message()

        if settings.deployment_mode == settings.Mode.SYN:
            # Use flasks thread-safe globals for access to the current message.
            g.current_message = msg

            logger.debug("Unpickled message is: {microservice_message}", extra={'microservice_message': msg})

            result = settings.ServiceWaypost.local_function(__message=msg)
            logger.debug("Synchronous result is: {result}", extra={'result': result})

            g.current_message = None
            return pickle.dumps(result)
        elif settings.deployment_mode == settings.Mode.ACTOR:
            # Kick off the process to do the work and send the response.
            logger.debug("Submitting work to executor")

            # Unlike the synchronous mode, we don't set the current_message variable in flask globals here because we're
            # going to handle it using thread locals in the async call.
            executor.submit(perform_service, msg)

            logger.debug("Asynchronous request has been scheduled.")
            # Ack the request.
            return pickle.dumps(True)
        raise ValueError("Invalid deployment mode: {}".format(settings.deployment_mode))

    # Now expose this function at the global scope so that it persists as a new flask route.
    new_service.name = service_name
    globals()[service_name] = new_service
    logger.debug("Created new service {service_name}", extra={'service_name': new_service})

    # Finally register this service with the local ServiceWaypost.
    func_name = service_name.split('.')[-1]
    mod_name = '.'.join(service_name.split('.')[:-1])
    mod = __import__(mod_name, globals(), locals(), [func_name], 0)
    func = getattr(mod, func_name)
    logger.debug("Dynamically found module is: {mod}", extra={'mod': mod})
    logger.debug("Dynamically found function is:{func}", extra={'func': func})
    settings.ServiceWaypost.local_service = service_name
    settings.ServiceWaypost.local_function = func


def initialise_microservice(service_name, host=None, port=None, **kwargs):
    from microservice.core.service_waypost import init_service_waypost

    host = host if host is not None else "0.0.0.0"
    port = port if port is not None else 5000
    logger.info("Starting service on {host}:{port}", extra={'host': host, 'port': port})

    configure_microservice()
    init_service_waypost()
    add_local_service(service_name)

    app.run(host=host, port=port, threaded=True)
