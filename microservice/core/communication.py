import requests


def send_to_uri(uri, *args, __action=None, **kwargs):
    json_data = {
        '_args': args,
        '_kwargs': kwargs,
        'action': __action,
    }
    print("Sending to uri %s:" % uri, json_data)
    result = requests.get(uri, json=json_data)
    if result:
        result = result.json()['_args']
    return result
