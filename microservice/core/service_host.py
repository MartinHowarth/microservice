import logging
import pickle
import requests
import threading

from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify

from microservice.core import settings, communication

logger = logging.getLogger(__name__)


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


def configure_microservice():
    """
    Configure the flask app. If this is called a second time, it tears down the existing app and re-creates it.
    """
    global app, executor
    app = Flask(__name__)
    if settings.communication_mode == settings.CommunicationMode.ACTOR:
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


def carry_out_local_service(message: communication.Message):
    # Actually carry out the service.
    try:
        logger.debug("Calling local function")
        result = settings.ServiceWaypost.local_function(__message=message)
        logger.debug("Result is: {result}", extra={'result': result})
    except communication.ServiceCallPerformed as e:
        logger.info("Nested service call complete: {nested_service}", extra={'nested_service', str(e)})
        result = None
    except Exception as err:
        logger.exception("Unexpected exception: {err}", exc_info=True, stack_info=True,  extra={'err': err})
        result = err
    return result


def perform_service(message: communication.Message):
    if message.via:
        return_service = message.via[-1].service_name
    else:
        # If there is no return service then we must be returning to the original calling party
        return_service = None

    logger.debug("Return service is: {return_service}", extra={'return_service': return_service})

    # Make the current message available globally
    # Note that this uses `threading.local()` to ensure that this message is only available to the current thread.
    settings.set_current_message(message)
    logger.debug("Original message is: {microservice_message}", extra={'microservice_message': message})

    # Actually carry out the service.
    result = carry_out_local_service(message)

    if result is not None:
        logger.info("No more nested microservices, returning.")

        # Send message back to calling party (which is the last via header)
        return_message = communication.construct_message_with_result(message, result)
        logger.debug("Return message is: {microservice_message}", extra={'microservice_message': message})
        communication.send_object_to_service(return_service, return_message)
    settings.set_current_message(None)


def handle_interface_callback(__message: communication.Message):
    """
    This handle receiving async call responses after they are made by a call from an non-microservice agent.

    It makes the result available to the thread waiting for the response to come in.
    :param __message:
    """
    logger.debug("Handling interface callback: {microservice_message}", extra={'microservice_message': __message})
    if __message.request_id in settings.interface_requests.keys():
        result_key = settings.interface_requests[__message.request_id]
        del settings.interface_requests[__message.request_id]
    else:
        raise RuntimeError("Received unexpected message. No corresponding request was made first.")
    logger.debug("Interface callback is for result_key: {result_key}", extra={'result_key': result_key})
    settings.set_interface_result(__message.request_id, __message.results[result_key])


def add_local_service(service_name, no_local_function=False):
    logger.info("Adding local service of name: {service_name}", extra={'service_name': service_name})

    # Define the flask app route for this service.
    @app.route('/')
    def new_service():
        logger.info("Service {service_name} received request", extra={'service_name': service_name})
        if request.data:
            msg = pickle.loads(request.data)
        else:
            msg = communication.Message()

        logger.debug("Unpickled message is: {microservice_message}", extra={'microservice_message': msg})

        if settings.communication_mode == settings.CommunicationMode.SYN:
            # Use flasks thread-safe globals for access to the current message.
            settings.set_current_message(msg)
            result = carry_out_local_service(msg)
            return_message = communication.Message(
                results={settings.ServiceWaypost.local_service: result}
            )
            logger.debug("Return message is: {microservice_message}", extra={'microservice_message': return_message})

            settings.set_current_message(None)
            return pickle.dumps(return_message)
        elif settings.communication_mode == settings.CommunicationMode.ACTOR:
            # Kick off the process to do the work and send the response.
            logger.debug("Submitting work to executor")

            # Unlike the synchronous mode, we don't set the current_message variable here because we're
            # going to handle it using thread locals in the async call.
            executor.submit(perform_service, msg)

            logger.debug("Asynchronous request has been scheduled.")
            # Ack the request.
            return pickle.dumps(True)
        raise ValueError("Invalid deployment mode: {}".format(settings.communication_mode))

    # Now expose this function at the global scope so that it persists as a new flask route.
    new_service.name = service_name
    globals()[service_name] = new_service
    logger.debug("Created new service {service_name}", extra={'service_name': service_name})

    settings.ServiceWaypost.local_service = service_name
    
    if no_local_function:
        logger.info("No local function set - this is likely an MS to non-MS interface handler.")
        settings.ServiceWaypost.local_function = handle_interface_callback
    else:
        func_name = service_name.split('.')[-1]
        mod_name = '.'.join(service_name.split('.')[:-1])
        mod = __import__(mod_name, globals(), locals(), [func_name], 0)
        func = getattr(mod, func_name)
        logger.debug("Dynamically found module is: {mod}", extra={'mod': mod})
        logger.debug("Dynamically found function is: {func}", extra={'func': func})
        settings.ServiceWaypost.local_function = func


def initialise_microservice(service_name, host=None, port=None, external_interface=False, **kwargs):
    from microservice.core.service_waypost import init_service_waypost

    host = host if host is not None else "0.0.0.0"
    port = port if port is not None else 5000
    logger.info("Starting service on {host}:{port}", extra={'host': host, 'port': port})

    configure_microservice()
    init_service_waypost()
    add_local_service(service_name, no_local_function=external_interface)

    # Not sure why this doesn't work if you define it in the global scope. It's nasty, but it works for now.
    @app.route('/ping')
    def ping():
        """
        Used for alive-ness checking.
        """
        return "pong"

    @app.route('/echo')
    def echo():
        """
        Echo the service name.
        """
        return service_name

    @app.route('/deployment_mode', methods=['GET', 'POST'])
    def deployment_mode():
        """
        GET settings.deployment_mode (read only)
        POST settings.deployment_mode (write and then read)

        This method is provided for testability. The deployment mode needs to change during testing, but when
        creating a microservice, the deployment mode is created with the default as defined in the settings and
        can't be overridden - without this function.
        """
        if request.method == 'GET':
            return settings.deployment_mode.value
        elif request.method == 'POST':
            new_deployment_mode = request.form['deployment_mode']
            logger.info("Setting deployment_mode to: {deployment_mode}", extra={'deployment_mode': new_deployment_mode})
            settings.deployment_mode = settings.DeploymentMode(new_deployment_mode)
            return settings.deployment_mode.value
        return "Method not allowed"

    @app.route('/deployment_manager_uri', methods=['GET', 'POST'])
    def deployment_manager_uri():
        """
        GET settings.ServiceWaypost.deployment_manager_uri (read only)
        POST settings.ServiceWaypost.deployment_manager_uri (write and then read)

        This method allows getting/setting of the deployment manager uri.
        """
        if request.method == 'GET':
            return settings.ServiceWaypost.deployment_manager_uri
        elif request.method == 'POST':
            new_deployment_manager_uri = request.form['deployment_manager_uri']
            logger.info("Setting deployment_manager_uri to: {deployment_manager_uri}",
                        extra={'deployment_manager_uri': new_deployment_manager_uri})
            settings.ServiceWaypost.deployment_manager_uri = new_deployment_manager_uri
            return settings.ServiceWaypost.deployment_manager_uri
        return "Method not allowed"

    @app.route('/terminate')
    def terminate():
        """
        Trigger this flask app to terminate.
        """
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
        return "Server shutting down..."

    # Start up flask in a thread so that execution can continue without blocking on flask.
    thrd = threading.Thread(
        target=app.run,
        kwargs={
            'host': host,
            'port': port,
            'threaded': True,
        })
    thrd.start()
    settings.flask_app_thread = thrd


def initialise_interface(service_name="interface", host=None, port=None):
    host = host if host is not None else "127.0.0.1"
    port = port if port is not None else 5000

    # Specifically set the local_uri because the service_name doesn't have any relevance for routing to n interface.
    settings.local_uri = "http://{}:{}/".format(host, port)
    logger.info("Initialising as an interface, found at uri: {local_uri}", extra={'local_uri': settings.local_uri})
    return initialise_microservice(service_name, host=host, port=port, external_interface=True)


def terminate_interface():
    requests.get(settings.local_uri + 'terminate')
    settings.flask_app_thread.join()
