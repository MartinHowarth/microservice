import json
from microservice import settings

from flask import Flask, request
app = Flask(__name__)


def initialise_microservice():
    for service in settings.local_services:
        print("Creating new service of name:", service)

        @app.route('/%s' % service, endpoint=service)
        def new_service():
            func_name = service.split('.')[-1]
            mod_name = '.'.join(service.split('.')[:-1])
            mod = __import__(mod_name, globals(), locals(), [func_name], 0)
            func = getattr(mod, func_name)
            print("Dynamically found module is:", mod)
            print("Dynamically found function is:", func)

            req_json = request.get_json()
            func_args = req_json.pop('_args')
            result = func(*func_args, **req_json)
            return json.dumps({'_args': result})

        new_service.name = service
        globals()[service] = new_service
        print("Created new service:", new_service)

    app.run()
