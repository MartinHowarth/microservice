from kubernetes import client, config
from kubernetes.client.rest import ApiException

from microservice.core import settings


kube_api_configuration = None


def uri_for_service(service_name: str) -> str:
    kube_name = sanitise_name(service_name)
    uri = 'http://{kube_name}.{namespace}/'.format(
        kube_name=kube_name,
        namespace=settings.kube_namespace,
    )
    return uri


def sanitise_name(name: str) -> str:
    """
    Change given service name into k8s compatible name, including:
      - 63 character limit
      - No '.', '_'
    :param name:
    :return:
    """
    name = name.replace('.', '-').replace('_', '-')
    if len(name) > 50:
        name = name[len(name) - 50:]

    # K8s requires an alphanumeric first character
    while not name[0].isalpha():
        name = name[1:]
    return name


class KubeMicroservice:
    def __init__(self, name: str, exposed: bool=False):
        # This must match the container name
        self.raw_name = name

        # K8s requires sanitised names for DNS purposes
        self.kube_name = sanitise_name(name)
        self.exposed = exposed

        self.api: client.CoreV1Api = None
        self.api_beta1: client.AppsV1beta1Api = None
        self.api_extensions_beta1: client.ExtensionsV1beta1Api = None
        self.api_autoscaling: client.AutoscalingV1Api = None

        self._service: client.V1Service = None
        self._deployment: client.AppsV1beta1Deployment = None
        self._ingress: client.V1beta1Ingress = None
        self._hpa: client.V1HorizontalPodAutoscaler = None

    def deploy(self):

        load_kube_config()

        self.api = client.CoreV1Api(client.ApiClient(config=kube_api_configuration))
        self.api_beta1 = client.AppsV1beta1Api(client.ApiClient(config=kube_api_configuration))
        self.api_extensions_beta1 = client.ExtensionsV1beta1Api(client.ApiClient(config=kube_api_configuration))
        self.api_autoscaling = client.AutoscalingV1Api(client.ApiClient(config=kube_api_configuration))

        self.create_service()
        self.create_deployment()
        self.create_hpa()
        if self.exposed:
            self.create_ingress()

    def create_service(self):
        try:
            self._service = self.api.create_namespaced_service(
                namespace=settings.kube_namespace,
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
                    namespace=settings.kube_namespace,
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
                namespace=settings.kube_namespace,
                body=self.deployment_definition,
                pretty=True,
            )
        except client.rest.ApiException as exp:
            if 'AlreadyExists' not in exp.body:
                raise
            print("MicroserviceCluster {0} already exists - patching.".format(self.kube_name))
            try:
                self.api_beta1.patch_namespaced_deployment(
                    name=self.kube_name,
                    namespace=settings.kube_namespace,
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
        try:
            self._ingress = self.api_extensions_beta1.create_namespaced_ingress(
                namespace=settings.kube_namespace,
                body=self.ingress_definition,
                pretty=True,
            )
        except client.rest.ApiException as exp:
            if 'AlreadyExists' not in exp.body:
                raise
            print("Ingress {0} already exists - patching.".format(self.kube_name))
            self._ingress = self.api_extensions_beta1.patch_namespaced_ingress(
                name=self.kube_name,
                namespace=settings.kube_namespace,
                body=self.ingress_definition,
                pretty=True,
            )

    def create_hpa(self):
        try:
            self._hpa = self.api_autoscaling.create_namespaced_horizontal_pod_autoscaler(
                namespace=settings.kube_namespace,
                body=self.hpa_definition,
                pretty=True,
            )
        except client.rest.ApiException as exp:
            if 'AlreadyExists' not in exp.body:
                raise
            print("HPA {0} already exists - patching.".format(self.kube_name))
            self._hpa = self.api_autoscaling.patch_namespaced_horizontal_pod_autoscaler(
                name=self.kube_name,
                namespace=settings.kube_namespace,
                body=self.hpa_definition,
                pretty=True,
            )

    @property
    def deployment_definition(self):
        return client.AppsV1beta1Deployment(
            metadata=client.V1ObjectMeta(
                name=self.kube_name,
                namespace=settings.kube_namespace,
                labels={'pycroservice': settings.kube_namespace},
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
                    namespace=settings.kube_namespace,
                    labels={'microservice': self.kube_name}
                ),
                spec=client.V1ServiceSpec(
                    type="NodePort" if self.exposed else None,
                    ports=[client.V1ServicePort(
                        name=self.kube_name,
                        port=80,
                        target_port=5000,
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
                    resources=client.V1ResourceRequirements(
                        requests={
                            'cpu': '100m',
                        },
                    ),
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
                    service_port=5000,
                )
            ),
        )

    @property
    def hpa_definition(self):
        return client.V1HorizontalPodAutoscaler(
            metadata=client.V1ObjectMeta(
                name=self.kube_name,
                namespace=settings.kube_namespace,
            ),
            spec=client.V1HorizontalPodAutoscalerSpec(
                min_replicas=1,
                max_replicas=100,
                scale_target_ref=client.V1CrossVersionObjectReference(
                    kind="MicroserviceCluster",
                    name=self.kube_name,
                ),
                target_cpu_utilization_percentage=50,
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
    if settings.kube_namespace not in [ns.metadata.name for ns in api.list_namespace().items]:
        print("Kube namespace {0} doesn't exist - creating...".format(settings.kube_namespace))
        api.create_namespace(
            client.V1Namespace(
                metadata={
                    'name': settings.kube_namespace,
                }
            ),
            pretty=True,
        )
        print("Kube namespace {0} created".format(settings.kube_namespace))
