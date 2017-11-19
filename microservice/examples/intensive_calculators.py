import random
import threading

from microservice.core.decorator import microservice

random.seed(42)


def sum_random_list(size):
    li = []

    # initialize random list with values between 0 and 100
    for i in range(size):
        li.append(random.randint(0, 10))

    return sum(li)


@microservice
def intensive_calculation_1():
    return sum_random_list(10000)


@microservice
def intensive_calculation_2(size):
    return sum_random_list(size)


@microservice
def intensive_calculation_3(size):
    return intensive_calculation_2(size)


@microservice
def intensive_calculator_fanout():
    results = {
        1: [],
        2: [],
        3: [],
    }

    def do_work1():
        res = intensive_calculation_1()
        print("Intensive calculation 1 says:", res)
        results[1].append(res)

    def do_work2():
        res = intensive_calculation_2(10000)
        print("Intensive calculation 2 says:", res)
        results[2].append(res)

    def do_work3():
        res = intensive_calculation_3(10000)
        print("Intensive calculation 3 says:", res)
        results[3].append(res)

    threads = []
    for i in range(100):
        thr = threading.Thread(target=do_work1)
        thr.start()
        threads.append(thr)
        thr = threading.Thread(target=do_work2)
        thr.start()
        threads.append(thr)
        thr = threading.Thread(target=do_work3)
        thr.start()
        threads.append(thr)

    for thr in threads:
        thr.join()

    return results
