import requests

from microservice.core.service_functions import service_uri_information


def send_to_uri(uri, *args, additional_json=None, **kwargs):
    json_data = {
        '_args': args,
        '_kwargs': kwargs,
    }
    if additional_json:
        json_data.update(additional_json)
    print("Sending to uri %s:" % uri, json_data)
    result = requests.get(uri, json=json_data)
    if result:
        result = result.json()['_args']
    print("Got result:", result)
    return result


def send_to_mgmt_of_uri(uri, *args, __action=None, **kwargs):
    mgmt_uri = service_uri_information(uri).management_uri
    action_json = {
        'action': __action,
    }
    return send_to_uri(mgmt_uri, *args, additional_json=action_json, **kwargs)
