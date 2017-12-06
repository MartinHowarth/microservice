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

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False

        return self.to_dict == other.to_dict


def send_to_uri(*args, __uri=None, **kwargs):
    json_data = {
        'args': args,
        'kwargs': kwargs,
        'via': [],
        'results': {},
    }
    print("Sending to uri %s:" % __uri, json_data)
    result = requests.get(__uri, json=json_data)
    if result:
        result = result.json()['args']
    print("Got result:", result)
    return result


def uri_from_service_name(service_name: str) -> str:
    kube_name = kube.sanitise_name(service_name)
    uri = 'http://{kube_name}.{namespace}/'.format(
        kube_name=kube_name,
        namespace=settings.kube_namespace,
    )
    return uri


def send_message_to_uri(uri: str, message: Message):
    result = requests.get(uri, json=message.to_dict)
    if result:
        result = result.json()['args']
    print("Got result:", result)
    return result


def send_message_to_service(service_name: str, message: Message):
    uri = uri_from_service_name(service_name)
    return send_message_to_uri(uri, message)


def construct_and_send_call_to_service(target_service, local_service, inbound_message, *args, **kwargs):
    via = inbound_message.via
    via.append(ViaHeader(
        local_service,
        inbound_message.args,
        inbound_message.kwargs,
    ))
    msg = Message(
        args=args,
        kwargs=kwargs,
        results=inbound_message.results,
        via=via,
    )
    send_message_to_service(target_service, msg)
