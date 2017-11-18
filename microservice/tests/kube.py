import time
import requests
from unittest import TestCase
from kubernetes import client, config


def wait_for(condition, interval=0.1, timeout=10):
    timer = 0
    while not condition():
        time.sleep(interval)
        timer += interval
        if timer > timeout:
            raise TimeoutError("Timeout waiting for condition %s" % condition)


class TestKubeIntegration(TestCase):
    test_namespace = 'testnamespace'

    def setUp(self):
        config.load_kube_config()
        configuration = client.Configuration()
        self.api = client.CoreV1Api(client.ApiClient(config=configuration))

        try:
            self.api.delete_namespace(
                self.test_namespace,
                client.V1DeleteOptions(
                    grace_period_seconds=0,
                    propagation_policy="Background",
                ),
                pretty=True
            )
        except:
            pass
        wait_for(lambda: self.test_namespace not in [ns.metadata.name for ns in self.api.list_namespace().items])

        # for pod in self.api.list_namespaced_pod(namespace=self.test_namespace, watch=False).items:
        #     self.api.delete_namespaced_pod(pod.metadata.name, pod.metadata.namespace, client.V1DeleteOptions(
        #         grace_period_seconds=0,
        #         propagation_policy="Background",
        #     ))
        # for serv in self.api.list_namespaced_service(namespace=self.test_namespace, watch=False).items:
        #     self.api.delete_namespaced_service(serv.metadata.name, serv.metadata.namespace)

    def test_nginx_service(self):
        self.api.create_namespace(
            client.V1Namespace(
                metadata={
                    'name': self.test_namespace,
                }
            )
        )
        wait_for(lambda: self.test_namespace in [ns.metadata.name for ns in self.api.list_namespace().items])
        print(self.api.list_namespace())
        print('!!!!')
        print(self.api.list_namespaced_secret(self.test_namespace))
        # time.sleep(5)

        self.api.create_namespaced_pod(
            self.test_namespace,
            client.V1Pod(
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="my-nginx",
                            image="nginx",
                            ports=[client.V1ContainerPort(80)],
                        ),
                    ]
                ),
                metadata=client.V1ObjectMeta(
                    name='my-nginx',
                    labels={'run': 'my-nginx'}
                )
            ),
            pretty=True
        )
        print([p.metadata.name for p in self.api.list_pod_for_all_namespaces(watch=False).items])

        self.api.create_namespaced_service(
            self.test_namespace,
            client.V1Service(
                metadata=client.V1ObjectMeta(
                    name='my-nginx-service',
                    namespace=self.test_namespace,
                    labels={'run': 'my-nginx'}
                ),
                spec=client.V1ServiceSpec(
                    external_i_ps=['192.168.99.100'],
                    ports=[client.V1ServicePort(port=80)],
                    selector={'run': 'my-nginx'},
                )
            ),
            pretty=True
        )

        self.assertEqual(requests.get('http://192.168.99.100:80').status_code, 200)

        self.api.delete_namespace(
            self.test_namespace,
            client.V1DeleteOptions(
                grace_period_seconds=0,
                propagation_policy="Background",
            ),
            pretty=True
        )

