from time import sleep

from microservice.core.decorator import microservice


def sleeper(length):
    print("Sleeping", length)
    sleep(length)
    return length


@microservice
def sleep_1():
    return sleeper(1)


@microservice
def sleep_3():
    return sleeper(3)


@microservice
def sleep_5():
    return sleeper(5)
