from microservice.core.decorator import microservice


@microservice
def hello_world(*args, **kwargs):
    return "Hello, world!"


@microservice
def hello_other_world(*args, **kwargs):
    return "Hello, other world!"
