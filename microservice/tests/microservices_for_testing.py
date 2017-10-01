from microservice.core.decorator import microservice


@microservice
def echo_as_dict(*args, **kwargs):
    ret = {'_args': args}
    ret.update(kwargs)
    return ret


@microservice
def echo_as_dict2(*args, **kwargs):
    ret = {'_args': args}
    ret.update(kwargs)
    ret2 = echo_as_dict(5, 2, 5, asdf="asdrf")
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
