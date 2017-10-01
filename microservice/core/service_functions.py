from collections import namedtuple


ServiceInformation = namedtuple("ServiceInformation", ["uri", "management_uri", "service_name"])


def service_uri_information(service_uri):
    """

    :param str service_uri:
    :return:
    """
    # If the uri doesn't end with a /<service_name> then just append __management instead of replacing anything
    if service_uri.count('/') > 2:
        service_name = service_uri.split('/')[-1]
        service_mgmt = service_uri.replace(service_name, '__management')
    else:
        service_name = None
        service_mgmt = service_uri + '/__management'
    return ServiceInformation(
        uri=service_uri,
        management_uri=service_mgmt,
        service_name=service_name
    )
