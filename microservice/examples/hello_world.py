from microservice.core.decorator import microservice


@microservice
def hello_world(*args, **kwargs):
    return "Hello, world!"
