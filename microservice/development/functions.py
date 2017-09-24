from microservice.core.decorator import microservice


@microservice
def echo_as_dict(*args, **kwargs):
    print(args)
    print(kwargs)
    ret = {'_args': args}
    ret.update(kwargs)
    return ret


@microservice
def echo_as_dict2(*args, **kwargs):
    print(args)
    print(kwargs)
    ret = {'_args': args}
    ret.update(kwargs)
    ret2 = echo_as_dict3(5, 2, 5, asdf="asdrf")
    return ret, ret2


@microservice
def echo_as_dict3(*args, **kwargs):
    print(args)
    print(kwargs)
    ret = {'_args': args}
    ret.update(kwargs)
    ret2 = echo_as_dict(234, 456, 345, ty="no problem")
    return ret, ret2
