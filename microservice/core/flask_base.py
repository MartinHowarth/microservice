import importlib
import json
from microservice.development import functions
import microservice.development.functions
from microservice import settings

from flask import Flask, request
app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/echo')
def echo():
    req_json = request.get_json()
    print("Request json is:", req_json)
    if req_json:
        resp = json.dumps(req_json)
    else:
        resp = "No json"
    print("Response is:", resp)
    return resp


settings.local_services = ["microservice.development.functions.echo_as_dict"]
func_to_serve = settings.local_services[0]
@app.route('/%s' % func_to_serve)
def echo_as_dict():
    func_name = func_to_serve.split('.')[-1]
    mod_name = '.'.join(func_to_serve.split('.')[:-1])
    mod = __import__(mod_name, globals(), locals(), [func_name], 0)
    func = getattr(mod, func_name)
    print("Dynamically found module is:", mod)
    print("Dynamically found function is:", func)

    req_json = request.get_json()
    args = req_json.pop('_args')
    result = func(*args, **req_json)
    return json.dumps({'_args': result})


def initialise_microservice():
    for service in settings.local_services:
        @app.route('/%s' % service)
        def new_service():
            func_name = service.split('.')[-1]
            mod_name = '.'.join(service.split('.')[:-1])
            mod = __import__(mod_name, globals(), locals(), [func_name], 0)
            func = getattr(mod, func_name)
            print("Dynamically found module is:", mod)
            print("Dynamically found function is:", func)

            req_json = request.get_json()
            args = req_json.pop('_args')
            result = func(*args, **req_json)
            return json.dumps({'_args': result})
        new_service.name = service


if __name__ == "__main__":
    # settings.local_services = ["echo_as_dict"]
    settings.local_services = ["microservice.development.functions.echo_as_dict"]
    # initialise_microservice()
    app.run()
