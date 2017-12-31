import docker

from io import BytesIO
from typing import List

client = docker.from_env()


base_dockerfile = """
FROM python:3

WORKDIR /usr/src/app

RUN git clone https://github.com/MartinHowarth/microservice.git \
  && cd microservice \
  && pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/usr/local/bin/microservice", "--host", "0.0.0.0", "--port", "5000", "--service"]
"""

pycroservice_dockerfile = """
FROM martinhowarth/microservice:latest

CMD ["{service_name}"]
"""


def build_image(dockerfile: str, tag: str, **kwargs) -> None:
    """
    Build a docker image from the given (string) dockerfile
    :param dockerfile:
    :param tag:
    :return:
    """
    fobj = BytesIO(dockerfile.encode('utf-8'))
    build = client.api.build(
        path="./",
        fileobj=fobj,
        forcerm=True,
        rm=True,
        tag=tag,
        **kwargs
    )
    if build:
        print("Docker build logs for {0} are:".format(tag))
        logs = []
        for bi in build:
            print(bi)
            logs.append(bi)
        if 'Successfully' not in str(logs[-1]):
            raise RuntimeError("Container {0} failed to build with error: {1}".format(tag, logs[-1]))


def build_all_images(service_names: List[str]) -> None:
    """
    Build a docker image for each microservice.

    :param service_names: List of service names.
    """
    # Build the base image first
    # build_image(
    #     base_dockerfile,
    #     'pycroservice:latest',
    #     pull=True,  # Pull updates to the base image
    # )

    for service_name in service_names:
        build_image(
            pycroservice_dockerfile.format(
                service_name=service_name
            ),
            "{0}:latest".format(service_name),
        )
