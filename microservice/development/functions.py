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
    return ret
