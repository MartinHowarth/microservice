import pickle
import requests

from collections import namedtuple

from microservice.core import kube, settings


class ServiceCallPerformed(Exception):
    pass


ViaHeader = namedtuple("ViaHeader", ['service_name', 'args', 'kwargs'])


class Message:
    def __init__(self, args=None, kwargs=None, via=None, results=None):
        self.args = args if args is not None else tuple()
        self.kwargs = kwargs if kwargs is not None else {}
        self.results = results if results is not None else {}

        if via is not None:
            self.via = [ViaHeader(v[0], v[1], v[2]) for v in via]
        else:
            self.via = []

    @classmethod
    def from_dict(cls, msg_json):
        return cls(**msg_json)

    @property
    def to_dict(self):
        return {
            'args': self.args,
            'kwargs': self.kwargs,
            'via': [(v.service_name, v.args, v.kwargs) for v in self.via],
            'results': self.results,
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

    def __str__(self):
        return str(self.to_dict)

    def __repr__(self):
        return str(self)


def uri_from_service_name(service_name: str) -> str:
    kube_name = kube.sanitise_name(service_name)
    uri = 'http://{kube_name}.{namespace}/'.format(
        kube_name=kube_name,
        namespace=settings.kube_namespace,
    )
    return uri


def send_object_to_service(service_name, obj):
    pickled = pickle.dumps(obj)
    uri = uri_from_service_name(service_name)
    result = requests.get(uri, data=pickled)
    if result:
        result = pickle.loads(result.content)
    print("Got result:", result)
    return result


def construct_message(local_service, inbound_message, *args, **kwargs):
    if inbound_message:
        via = inbound_message.via
        via.append(ViaHeader(
            local_service,
            inbound_message.args,
            inbound_message.kwargs,
        ))
        results = inbound_message.results
    else:
        via = None
        results = None

    return Message(
        args=args,
        kwargs=kwargs,
        results=results,
        via=via,
    )


def construct_and_send_call_to_service(target_service, local_service, inbound_message, *args, **kwargs):
    msg = construct_message(local_service, inbound_message, *args, **kwargs)
    print("Constructed message: {}".format(msg))
    return send_object_to_service(target_service, msg)
