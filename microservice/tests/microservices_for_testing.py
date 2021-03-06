import sys

from microservice.core.decorator import microservice


echo_as_dict2_args = (5, 2, 5)
echo_as_dict2_kwargs = {'asdf': "asdrf"}


@microservice
def echo_as_dict(*args, **kwargs):
    ret = {'_args': args}
    ret.update(kwargs)
    return ret


@microservice
def echo_as_dict2(*args, **kwargs):
    ret = {'_args': args}
    ret.update(kwargs)
    print("Calling into `echo_as_dict`")
    ret2 = echo_as_dict(*echo_as_dict2_args, **echo_as_dict2_kwargs)
    return ret, ret2


@microservice
def echo_as_dict3(*args, **kwargs):
    ret = {'_args': args}
    ret.update(kwargs)
    ret2 = echo_as_dict2(234, 456, 345, ty="no problem")
    return ret, ret2


@microservice
def echo_as_dict4(*args, **kwargs):
    ret = {'_args': args}
    ret.update(kwargs)
    ret2 = echo_as_dict3(234, 456, 345, ty="no problem")
    return ret, ret2


@microservice
def echo_as_dict5(*args, **kwargs):
    ret = {'_args': args}
    ret.update(kwargs)
    ret2 = echo_as_dict2(234, 456, 345, ty="no problem")
    ret3 = echo_as_dict3(234, 456, 345, ty="no problem")
    return ret, ret2, ret3


@microservice
def exception_raiser(*args, **kwargs):
    raise RuntimeError("Called with: {}; {}".format(args, kwargs))


all_test_microservices = [
    'microservice.tests.microservices_for_testing.echo_as_dict',
    'microservice.tests.microservices_for_testing.echo_as_dict2',
    'microservice.tests.microservices_for_testing.echo_as_dict3',
    'microservice.tests.microservices_for_testing.echo_as_dict4',
    'microservice.tests.microservices_for_testing.echo_as_dict5',
    'microservice.tests.microservices_for_testing.exception_raiser',
]
