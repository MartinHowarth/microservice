from collections import defaultdict

from microservice.core.communication import send_to_mgmt_of_uri
from microservice.core.decorator import microservice


class PubSubFunctions:
    PUBLISH = 'publish'
    SUBSCRIBE = 'subscribe'
    UNSUBSCRIBE = 'unsubscribe'
    PURGE = 'purge'


class _PubSub:
    consumers = defaultdict(list)

    def handle_subscribe(self, event_type, consumer):
        print("Received subscribe for event %s from:" % event_type, consumer)
        self.consumers[event_type].append(consumer)

    def handle_unsubscribe(self, event_type, consumer):
        print("Received unsubscribe for event %s from:" % event_type, consumer)
        try:
            self.consumers[event_type].remove(consumer)
        except ValueError:
            pass

    def handle_publish(self, event_type, *args, **kwargs):
        print("Received publish for event %s:" % event_type, args, kwargs)
        print("Consumers of this event type are:", self.consumers[event_type])
        for consumer in self.consumers[event_type]:
            self.notify_consumer(consumer, *args, **kwargs)

    def notify_consumer(self, consumer, *args, **kwargs):
        result = send_to_mgmt_of_uri(consumer, *args, **kwargs)

    def handle_purge(self, consumer):
        for event_type, consumers in self.consumers.items():
            if consumer in consumers:
                consumers.remove(consumer)


PubSub = _PubSub()


@microservice
def _send_to_pubsub(signal, *args, __consumer=None, __event_type=None, **kwargs):
    print(signal, args, __consumer, __event_type, kwargs)
    if signal == PubSubFunctions.SUBSCRIBE:
        PubSub.handle_subscribe(__event_type, __consumer)
    elif signal == PubSubFunctions.UNSUBSCRIBE:
        PubSub.handle_unsubscribe(__event_type, __consumer)
    elif signal == PubSubFunctions.PUBLISH:
        PubSub.handle_publish(__event_type, *args, **kwargs)
    elif signal == PubSubFunctions.PURGE:
        PubSub.handle_purge(__consumer)


def publish(event_type, *args, **kwargs):
    print("Publishing about %s:" % event_type, args, kwargs)
    return _send_to_pubsub(PubSubFunctions.PUBLISH, *args, __event_type=event_type, **kwargs)


def subscribe(event_type, consumer):
    print("%s is subscribing to:" % consumer, event_type)
    return _send_to_pubsub(PubSubFunctions.SUBSCRIBE, __event_type=event_type, __consumer=consumer)


def unsubscribe(event_type, consumer):
    print("%s is unsubscribing from:" % consumer, event_type)
    return _send_to_pubsub(PubSubFunctions.UNSUBSCRIBE, __event_type=event_type, __consumer=consumer)


def purge(consumer):
    print("%s is being purged." % consumer)
    return _send_to_pubsub(PubSubFunctions.PURGE, __consumer=consumer)
