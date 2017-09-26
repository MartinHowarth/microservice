import random

from microservice.core.decorator import microservice

random.seed(42)


def sum_random_list(size):
    li = []

    # initialize random list with values between 0 and 100
    for i in range(size):
        li.append(random.randint(0, 10))

    return sum(li)


@microservice
def intensive_calculation_1(size):
    return sum_random_list(size)


@microservice
def intensive_calculation_2(size):
    return sum_random_list(size)


@microservice
def intensive_calculation_3(size):
    return intensive_calculation_2(size)
