from microservice.core.decorator import microservice


@microservice
def hello_world(*args, stop=False):
    if stop:
        return "Hello, world - final!"

    import requests
    req = requests.get(
        "http://microservice-examples-hello-world-hello-world.pycroservices:5000/microservice.examples.hello_world.hello_world",
        json={
            '_args': tuple(),
            '_kwargs': {'stop': True},
        }
    )
    print(req)
    print(req.text)
    return "Hello, world!"
