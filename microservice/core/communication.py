import logging
import pickle
import requests
import time

from collections import namedtuple
from typing import List

from microservice.core import kube, settings

logger = logging.getLogger(__name__)


class ServiceCallPerformed(Exception):
    pass


ResultKey = namedtuple("ResultKey", ['service_name', 'args', 'kwargs'])
ViaHeader = namedtuple("ViaHeader", ['service_name', 'args', 'kwargs'])


def create_result_key(service_name, args, kwargs):
    return ResultKey(service_name, pickle.dumps(args), pickle.dumps(kwargs))


def generate_request_id():
    return time.time()


class Message:
    def __init__(self, args=None, kwargs=None, via=None, results=None, request_id=None):
        self.args = args if args is not None else tuple()
        self.kwargs = kwargs if kwargs is not None else dict()
        self.results = results if results is not None else dict()
        self.request_id = request_id if request_id is not None else generate_request_id()

        if via is not None:
            self.via = [ViaHeader(v[0], v[1], v[2]) for v in via]
        else:
            self.via = []

    @classmethod
    def from_dict(cls, msg_dict: dict):
        return cls(**msg_dict)

    @property
    def to_dict(self):
        return {
            'args': self.args,
            'kwargs': self.kwargs,
            'via': [(v.service_name, v.args, v.kwargs) for v in self.via],
            'results': self.results,
            'request_id': self.request_id,
        }

    @classmethod
    def unpickle(cls, msg_pickle):
        return pickle.loads(msg_pickle)

    @property
    def pickle(self):
        return pickle.dumps(self)

    def add_result(self, service_name, args, kwargs, result):
        """
        Repeated calls to the same function with different args/kwargs can have different results, so we need
        to record them separately.

        :param service_name:
        :param args:
        :param kwargs:
        :param result:
        """
        key = create_result_key(service_name, args, kwargs)
        self.results[key] = result

    def get_result(self, service_name, args, kwargs):
        key = create_result_key(service_name, args, kwargs)
        return self.results[key]

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False

        return self.to_dict == other.to_dict

    def __repr__(self):
        kwargs = ', '.join(["{}={}".format(key, value) for key, value in self.to_dict.items()])
        return "{}({})".format(self.__class__.__name__, kwargs)

    def human_results(self) -> List[str]:
        """
        Helper method to format the results in a human-readable format.
        """
        results = self.to_dict['results']
        parsed_results = []
        for res_key, res in results.items():
            service_name = res_key.service_name
            args = tuple(pickle.loads(res_key.args))
            kwargs = pickle.loads(res_key.kwargs)
            args_str = ', '.join(str(a) for a in args)
            kwargs_str = ', '.join(['{}={}'.format(k, v) for k, v in kwargs.items()])
            parsed_results.append("{}({}, {}) = {}".format(service_name, args_str, kwargs_str, res))

        return parsed_results


def uri_from_service_name(service_name: str) -> str:
    if settings.deployment_mode == settings.DeploymentMode.KUBERNETES:
        return kube.uri_for_service(service_name)
    elif settings.deployment_mode == settings.DeploymentMode.SUBPROCESS:
        if settings.ServiceWaypost.deployment is not None:
            # We are running as the deployment manager.
            uri = settings.ServiceWaypost.deployment.uri_for_service(service_name)
        elif service_name not in settings.ServiceWaypost.service_uris.keys():
            # We are running as a subprocess service and we haven't cached the uri for `service_name`
            request_uri = settings.ServiceWaypost.deployment_manager_uri + 'uri/' + service_name
            uri = requests.get(request_uri).text
            logger.info("Discovered subprocess service uri for {service_name} as: {service_uri}",
                        extra={'service_name': service_name, 'service_uri': uri})
            settings.ServiceWaypost.service_uris[service_name] = uri
        else:
            # We are running as a subprocess service and we have already cached the uri for `service_name`
            uri = settings.ServiceWaypost.service_uris[service_name]
        return uri
    raise ValueError("Invalid deployment_mode.")


def get_local_uri() -> str:
    """
    :return: The local uri, if specified, otherwise the local service name.
    """
    if settings.local_uri is not None:
        logger.debug("Local uri has been specifically set: {local_uri}", extra={'local_uri': settings.local_uri})
        return settings.local_uri
    return settings.ServiceWaypost.local_service


def send_object_to_service(service_name: str, obj) -> tuple:
    logger.debug("Sending object to service: {service_name}: {obj}", extra={'service_name': service_name, 'obj': obj})
    pickled = pickle.dumps(obj)
    if service_name.startswith('http'):
        logger.debug("Via header service name is already a URI")
        uri = service_name
    else:
        uri = uri_from_service_name(service_name)
    logger.debug("Service is found at: {service_uri}", extra={'service_uri': uri})
    result = requests.get(uri, data=pickled)
    if result:
        result = pickle.loads(result.content)
    logger.debug("Got result: {result}", extra={'result': result})
    return result


def construct_message_with_result(inbound_message: Message, result) -> Message:
    return_args = inbound_message.via[-1].args
    return_kwargs = inbound_message.via[-1].kwargs
    results = inbound_message.results.copy()
    msg = Message(
        args=return_args,
        kwargs=return_kwargs,
        via=inbound_message.via[:-1],
        results=results,
        request_id=inbound_message.request_id,
    )
    msg.add_result(settings.ServiceWaypost.local_service,
                   inbound_message.args,
                   inbound_message.kwargs,
                   result)
    logger.debug("Constructed message with result: {microservice_message}", extra={'microservice_message': msg})
    return msg


def construct_message_add_via(inbound_message: Message, *args, **kwargs) -> Message:
    if inbound_message:
        via = inbound_message.via
        via.append(ViaHeader(
            get_local_uri(),
            inbound_message.args,
            inbound_message.kwargs,
        ))
        results = inbound_message.results
        request_id = inbound_message.request_id
    else:
        logger.warning("Shouldn't ever be here, I think...")
        via = None
        results = None
        request_id = None

    msg = Message(
        args=args,
        kwargs=kwargs,
        results=results,
        via=via,
        request_id=request_id
    )
    logger.debug("Constructed message added via: {microservice_message}", extra={'microservice_message': msg})
    return msg


def construct_and_send_call_to_service(target_service: str, inbound_message: Message, *args, **kwargs) -> tuple:
    logger.debug("Sending message to service.")
    msg = construct_message_add_via(inbound_message, *args, **kwargs)
    return send_object_to_service(target_service, msg)
