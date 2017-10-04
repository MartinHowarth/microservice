from unittest import TestCase
from unittest.mock import MagicMock, call

from microservice.core import settings, pubsub
from microservice.core.pubsub import PubSub
from microservice.core.service_waypost import init_service_waypost


class TestPubSub(TestCase):
    def setUp(self):
        init_service_waypost(disable_heartbeating=True)
        settings.deployment_type = settings.DeploymentType.ZERO

        self.original_notify_consumer = PubSub.notify_consumer
        self.mocked_notify_consumer = MagicMock()
        PubSub.notify_consumer = self.mocked_notify_consumer

    def tearDown(self):
        PubSub.notify_consumer = self.original_notify_consumer

    def test_PubSub(self):
        with self.subTest(msg="Test subscribe"):
            PubSub.handle_subscribe("event_1", "consumer_1")
            PubSub.handle_subscribe("event_1", "consumer_2")
            PubSub.handle_subscribe("event_2", "consumer_1")

            self.assertEqual(
                PubSub.consumers,
                {
                    'event_1': ['consumer_1', 'consumer_2'],
                    'event_2': ['consumer_1'],
                }
            )

        with self.subTest(msg="Test publish"):
            args = (5, 6, 7)
            kwargs = {
                'apple': "tasty",
                'banana': "loaf",
            }
            PubSub.handle_publish("event_1", *args, **kwargs)
            call_1 = call("consumer_1", *args, **kwargs)
            call_2 = call("consumer_2", *args, **kwargs)
            self.mocked_notify_consumer.assert_has_calls([call_1, call_2], any_order=True)

            PubSub.handle_publish("event_2", *args, **kwargs)
            call_1 = call("consumer_1", *args, **kwargs)
            self.mocked_notify_consumer.assert_has_calls([call_1], any_order=True)

        with self.subTest(msg="Test unsubscribe"):
            PubSub.handle_unsubscribe("event_1", "consumer_1")
            self.assertEqual(
                PubSub.consumers,
                {
                    'event_1': ['consumer_2'],
                    'event_2': ['consumer_1'],
                }
            )

            PubSub.handle_unsubscribe("event_1", "consumer_2")
            self.assertEqual(
                PubSub.consumers,
                {
                    'event_1': [],
                    'event_2': ['consumer_1'],
                }
            )

        PubSub.handle_subscribe("event_1", "consumer_1")
        PubSub.handle_subscribe("event_2", "consumer_2")
        with self.subTest(msg="Test purge"):
            PubSub.handle_purge("consumer_1")
            self.assertEqual(
                PubSub.consumers,
                {
                    'event_1': [],
                    'event_2': ['consumer_2'],
                }
            )

            PubSub.handle_purge("consumer_2")
            self.assertEqual(
                PubSub.consumers,
                {
                    'event_1': [],
                    'event_2': [],
                }
            )
            PubSub.handle_purge("consumer_3")


class TestPubSubHelpers(TestCase):
    def setUp(self):
        init_service_waypost(disable_heartbeating=True)
        settings.deployment_type = settings.DeploymentType.ZERO

        self.original_handle_publish = PubSub.handle_publish
        self.mocked_handle_publish = MagicMock()
        PubSub.handle_publish = self.mocked_handle_publish

        self.original_handle_subscribe = PubSub.handle_subscribe
        self.mocked_handle_subscribe = MagicMock()
        PubSub.handle_subscribe = self.mocked_handle_subscribe

        self.original_handle_purge = PubSub.handle_purge
        self.mocked_handle_purge = MagicMock()
        PubSub.handle_purge = self.mocked_handle_purge

    def tearDown(self):
        PubSub.handle_publish = self.original_handle_publish
        PubSub.handle_subscribe = self.original_handle_subscribe

    def test_publish(self):
        args = (5, 6, 7)
        kwargs = {
            'apple': "tasty",
            'banana': "loaf",
        }

        pubsub.publish("event_1", *args, **kwargs)
        pubsub.publish("service_name", "http://127.0.0.1:5000/test", __action='receive_service_advertisement')

        self.mocked_handle_publish.assert_has_calls([
            call("event_1", *args, **kwargs),
            call("service_name", "http://127.0.0.1:5000/test", __action='receive_service_advertisement')
        ])

    def test_subscribe(self):
        pubsub.subscribe("event_1", "consumer_1")

        self.mocked_handle_subscribe.assert_has_calls([call("event_1", "consumer_1")])

    def test_purge(self):
        pubsub.purge("consumer_1")

        self.mocked_handle_purge.assert_has_calls([call("consumer_1")])
