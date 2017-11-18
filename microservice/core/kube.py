from kubernetes import client, config
from kubernetes.client.rest import ApiException
from pprint import pprint

from microservice.core.settings import kube_name


kube_api_configuration = None


class KubeMicroservice:
    def __init__(self, name, exposed=False):
        load_kube_config()

        self.name = name
        self.exposed = exposed

        self.api = client.CoreV1Api(client.ApiClient(config=kube_api_configuration))
        self.api_beta1 = client.AppsV1beta1Api(client.ApiClient(config=kube_api_configuration))

    def deploy(self):
        self.create_service()
        self.create_deployment()

    def create_service(self):
        self.api.create_namespaced_service(
            namespace=kube_name,
            body=self.service_definition
        )

    def create_deployment(self):
        self.api_beta1.create_namespaced_deployment(
            namespace=kube_name,
            body=self.deployment_definition
        )

    @property
    def deployment_definition(self):
        return client.AppsV1beta1Deployment(
            metadata=client.V1ObjectMeta(
                name=self.name,
                namespace=kube_name,
                labels={'microservice': self.name},
            ),
            spec=client.AppsV1beta1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={'microservice': self.name},
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={'microservice': self.name},
                    ),
                    spec=self.pod_spec,
                ),
            )
        )

    @property
    def service_definition(self):
        return client.V1Service(
                metadata=client.V1ObjectMeta(
                    name=self.name,
                    namespace=kube_name,
                    labels={'microservice': self.name}
                ),
                spec=client.V1ServiceSpec(
                    external_traffic_policy="NodePort" if self.exposed else None,
                    # external_i_ps=['192.168.99.100'],
                    ports=[client.V1ServicePort(port=80)],
                    selector={'microservice': self.name},
                )
            )

    @property
    def startup_command(self):
        return "microservice --host %s --port %s --local_services %s" % (
            "0.0.0.0", 80, self.name)

    # @property
    # def pod_definition(self):
    #     return client.V1Pod(
    #             spec=self.pod_spec,
    #             metadata=client.V1ObjectMeta(
    #                 name=self.name,
    #                 labels={'microservice': self.name}
    #             )
    #         )

    @property
    def pod_spec(self):
        return client.V1PodSpec(
            containers=[
                client.V1Container(
                    name=self.name,
                    image=kube_name,
                    ports=[client.V1ContainerPort(80)],
                    args=['/bin/sh', '-c', self.startup_command],
                ),
            ]
        )


def load_kube_config():
    global kube_api_configuration
    if kube_api_configuration is not None:
        return

    config.load_kube_config()
    kube_api_configuration = client.Configuration()


def create_all_deployments(service_names):
    for service_name in service_names:
        kms = KubeMicroservice(service_name)
        kms.deploy()


def pycroservice_init():
    load_kube_config()

    api = client.CoreV1Api(client.ApiClient(config=kube_api_configuration))
    if kube_name not in [ns.metadata.name for ns in api.list_namespace().items]:
        print("Kube namespace {0} doesn't exist - creating...".format(kube_name))
        api.create_namespace(
            client.V1Namespace(
                metadata={
                    'name': kube_name,
                }
            )
        )
        print("Kube namespace {0} created".format(kube_name))


#
# config.load_kube_config()
#
# # Configure API key authorization: BearerToken
# # client.configuration.api_key['authorization'] = 'YOUR_API_KEY'
# # Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# # kubernetes.client.configuration.api_key_prefix['authorization'] = 'Bearer'
# # create an instance of the API class
# api_instance = client.AdmissionregistrationApi()
#
# try:
#     api_response = api_instance.get_api_group()
#     pprint(api_response)
# except ApiException as e:
#     print("Exception when calling AdmissionregistrationApi->get_api_group: %s\n" % e)
#
#
# # config.load_kube_config()
#
# # v1 = client.CoreV1Api()
#
#
# def deploy_microservice(service_name):
#     configuration = client.Configuration()
#     api_instance = client.CoreV1Api(client.ApiClient(configuration))
#     namespace = 'microservice'
#     body = client.V1Service()
#
#
#
# def create_service(service_name):
#     configuration = client.Configuration()
#     api_instance = client.CoreV1Api(client.ApiClient(configuration))
#     namespace = 'namespace_example'  # str | object name and auth scope, such as for teams and projects
#     body = client.V1Service()  # V1Service |
#     pretty = 'pretty_example'  # str | If 'true', then the output is pretty printed. (optional)
#
#     try:
#         api_response = api_instance.create_namespaced_service(namespace, body, pretty=pretty)
#         pprint(api_response)
#     except ApiException as e:
#         print("Exception when calling CoreV1Api->create_namespaced_service: %s\n" % e)
#
# def create_ingress(external_ip, external_port):
#     pass
#
#
# def list_all_pods():
#     configuration = client.Configuration()
#     api_instance = client.CoreV1Api(client.ApiClient(config=configuration))
#     print("Listing pods with their IPs:")
#     ret = api_instance.list_pod_for_all_namespaces(watch=False)
#     for i in ret.items:
#         print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
#
#
# def list_all_services():
#     configuration = client.Configuration()
#     api_instance = client.CoreV1Api(client.ApiClient(config=configuration))
#     print("Listing services with their IPs:")
#     ret = api_instance.list_service_for_all_namespaces(watch=False)
#     for i in ret.items:
#         print("%s\t%s\t%s" % (i.spec.cluster_ip, i.metadata.namespace, i.metadata.name))
#
#
# def list_all_namespaces():
#     configuration = client.Configuration()
#     api_instance = client.CoreV1Api(client.ApiClient(config=configuration))
#     print("Listing pods with their IPs:")
#     ret = api_instance.list_namespace(watch=False)
#     for i in ret.items:
#         print("%s" % ( i.metadata.name))
#
# list_all_pods()
# list_all_services()
#
# import requests
#
# print(requests.get('http://192.168.99.100:80').text)
