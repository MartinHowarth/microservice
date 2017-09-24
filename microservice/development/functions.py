from microservice.core.decorator import microservice


@microservice
def echo_as_dict(*args, **kwargs):
    print(args)
    print(kwargs)
    ret = {'_args': args}
    ret.update(kwargs)
    return ret


if __name__ == "__main__":

    print("Echo as dict says: %s" % echo_as_dict(1, 2, 3, apple=5, banana="cabbage"))
