import logging
import pickle
import random
import requests

from collections import namedtuple

from microservice.core import kube, settings

logger = logging.getLogger(__name__)


class ServiceCallPerformed(Exception):
    pass


ViaHeader = namedtuple("ViaHeader", ['service_name', 'args', 'kwargs'])


class Message:
    def __init__(self, args=None, kwargs=None, via=None, results=None, request_id=None):
        self.args = args if args is not None else tuple()
        self.kwargs = kwargs if kwargs is not None else {}
        self.results = results if results is not None else {}
        self.request_id = request_id if request_id is not None else random.randint(10000000, 99999999)

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

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False

        return self.to_dict == other.to_dict

    def __repr__(self):
        kwargs = ', '.join(["{}={}".format(key, value) for key, value in self.to_dict.items()])
        return "{}({})".format(self.__class__.__name__, kwargs)


def uri_from_service_name(service_name: str) -> str:
    kube_name = kube.sanitise_name(service_name)
    uri = 'http://{kube_name}.{namespace}/'.format(
        kube_name=kube_name,
        namespace=settings.kube_namespace,
    )
    return uri


def send_object_to_service(service_name: str, obj) -> tuple:
    logger.debug("Sending object to service: {service_name}: {obj}", extra={'service_name': service_name, 'obj': obj})
    pickled = pickle.dumps(obj)
    uri = uri_from_service_name(service_name)
    result = requests.get(uri, data=pickled)
    if result:
        result = pickle.loads(result.content)
    logger.debug("Got result: {result}", extra={'result': result})
    return result


def construct_message_with_result(inbound_message: Message, result: tuple) -> Message:
    return_args = inbound_message.via[-1].args
    return_kwargs = inbound_message.via[-1].kwargs
    results = inbound_message.results.copy()
    results.update({
        settings.ServiceWaypost.local_service: result
    })
    msg = Message(
        args=return_args,
        kwargs=return_kwargs,
        via=inbound_message.via[:-1],
        results=results,
        request_id=inbound_message.request_id,
    )
    logger.debug("Constructed message with result: {microservice_message}", extra={'microservice_message': msg})
    return msg


def construct_message_add_via(local_service: str, inbound_message: Message, *args, **kwargs) -> Message:
    if inbound_message:
        via = inbound_message.via
        via.append(ViaHeader(
            local_service,
            inbound_message.args,
            inbound_message.kwargs,
        ))
        results = inbound_message.results
        request_id = inbound_message.request_id
    else:
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


def construct_and_send_call_to_service(target_service: str, local_service: str, inbound_message: Message,
                                       *args,
                                       **kwargs) -> tuple:
    logger.debug("Sending message to service.")
    msg = construct_message_add_via(local_service, inbound_message, *args, **kwargs)
    return send_object_to_service(target_service, msg)
