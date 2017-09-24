import json
from microservice.development import functions
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


@app.route('/echo_as_dict')
def echo_as_dict():
    req_json = request.get_json()
    args = req_json.pop('_args')
    result = functions.echo_as_dict(*args, **req_json)
    return json.dumps({'_args': result})


if __name__ == "__main__":
    settings.local_services = ["echo_as_dict"]
    app.run()
