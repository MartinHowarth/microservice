from kubernetes import client, config
from kubernetes.client.rest import ApiException

from microservice.core.settings import kube_namespace


kube_api_configuration = None


class KubeMicroservice:
    def __init__(self, name, exposed_port=None):
        # This must match the container name
        self.raw_name = name

        # K8s requires sanitised names for DNS purposes
        self.kube_name = name.replace('.', '-').replace('_', '-')
        self.exposed_port = exposed_port

        self.api: client.CoreV1Api = None
        self.api_beta1: client.AppsV1beta1Api = None
        self.api_extensions_beta1: client.ExtensionsV1beta1Api = None

        self._service: client.V1Service = None
        self._deployment: client.AppsV1beta1Deployment = None
        self._ingress: client.V1beta1Ingress = None

    def deploy(self):

        load_kube_config()

        self.api = client.CoreV1Api(client.ApiClient(config=kube_api_configuration))
        self.api_beta1 = client.AppsV1beta1Api(client.ApiClient(config=kube_api_configuration))
        self.api_extensions_beta1 = client.ExtensionsV1beta1Api(client.ApiClient(config=kube_api_configuration))

        self.create_service()
        self.create_deployment()
        if self.exposed_port is not None:
            self.create_ingress()

    def create_service(self):
        try:
            self._service = self.api.create_namespaced_service(
                namespace=kube_namespace,
                body=self.service_definition,
                pretty=True,
            )
        except client.rest.ApiException as exp:
            if 'AlreadyExists' not in exp.body:
                raise
            print("Service {0} already exists - patching.".format(self.kube_name))
            try:
                self.api.patch_namespaced_service(
                    name=self.kube_name,
                    namespace=kube_namespace,
                    body=self.service_definition,
                    pretty=True,
                )
            except client.rest.ApiException as exp2:
                if 'FieldValueDuplicate' in exp2.body:
                    print("Possible cause:"
                          "Patching mechanism doesn't cope with changing ports (it tries to add a second one) - "
                          "manually delete the service resource and try again.")
                raise

    def create_deployment(self):
        try:
            self._deployment = self.api_beta1.create_namespaced_deployment(
                namespace=kube_namespace,
                body=self.deployment_definition,
                pretty=True,
            )
        except client.rest.ApiException as exp:
            if 'AlreadyExists' not in exp.body:
                raise
            print("Deployment {0} already exists - patching.".format(self.kube_name))
            try:
                self.api_beta1.patch_namespaced_deployment(
                    name=self.kube_name,
                    namespace=kube_namespace,
                    body=self.deployment_definition,
                    pretty=True,
                )
            except client.rest.ApiException as exp2:
                if 'FieldValueDuplicate' in exp2.body:
                    print("Possible cause:"
                          "Patching mechanism doesn't cope with changing ports (it tries to add a second one) - "
                          "manually delete the deployment and pod resources and try again.")
                raise

    def create_ingress(self):
        """
        Create an ingress for this service.
        :return:
        """
        try:
            self._ingress = self.api_extensions_beta1.create_namespaced_ingress(
                namespace=kube_namespace,
                body=self.ingress_definition,
                pretty=True,
            )
        except client.rest.ApiException as exp:
            if 'AlreadyExists' not in exp.body:
                raise
            print("Ingress {0} already exists - patching.".format(self.kube_name))
            self._ingress = self.api_extensions_beta1.patch_namespaced_ingress(
                name=self.kube_name,
                namespace=kube_namespace,
                body=self.ingress_definition,
                pretty=True,
            )

    @property
    def deployment_definition(self):
        return client.AppsV1beta1Deployment(
            metadata=client.V1ObjectMeta(
                name=self.kube_name,
                namespace=kube_namespace,
                labels={'pycroservice': kube_namespace},
            ),
            spec=client.AppsV1beta1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={'microservice': self.kube_name},
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={'microservice': self.kube_name},
                    ),
                    spec=self.pod_spec,
                ),
            )
        )

    @property
    def service_definition(self):
        return client.V1Service(
                metadata=client.V1ObjectMeta(
                    name=self.kube_name,
                    namespace=kube_namespace,
                    labels={'microservice': self.kube_name}
                ),
                spec=client.V1ServiceSpec(
                    type="LoadBalancer" if self.exposed_port else None,
                    ports=[client.V1ServicePort(
                        name=self.kube_name,
                        port=5000,
                    )],
                    selector={'microservice': self.kube_name},
                )
            )

    @property
    def pod_spec(self):
        return client.V1PodSpec(
            containers=[
                client.V1Container(
                    name=self.kube_name,
                    image=self.raw_name,
                    ports=[client.V1ContainerPort(container_port=5000)],
                    image_pull_policy='Never',
                ),
            ]
        )

    @property
    def ingress_definition(self):
        return client.V1beta1Ingress(
            metadata=client.V1ObjectMeta(
                name=self.kube_name
            ),
            spec=client.V1beta1IngressSpec(
                backend=client.V1beta1IngressBackend(
                    service_name=self.kube_name,
                    service_port=self.exposed_port,
                )
            ),
        )


def load_kube_config():
    global kube_api_configuration
    if kube_api_configuration is not None:
        return

    config.load_kube_config()
    kube_api_configuration = client.Configuration()


def pycroservice_init():
    """
    Initialise the generic k8s requirements for a new pycroservice deployment.
    Specifically:
     - Ensure that the namespace exists
    """
    load_kube_config()

    api = client.CoreV1Api(client.ApiClient(config=kube_api_configuration))
    if kube_namespace not in [ns.metadata.name for ns in api.list_namespace().items]:
        print("Kube namespace {0} doesn't exist - creating...".format(kube_namespace))
        api.create_namespace(
            client.V1Namespace(
                metadata={
                    'name': kube_namespace,
                }
            ),
            pretty=True,
        )
        print("Kube namespace {0} created".format(kube_namespace))
