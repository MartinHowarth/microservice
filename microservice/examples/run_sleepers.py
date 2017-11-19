"""
In ZERO mode, this takes 5 seconds to run. This is because we spin up all threads (14) concurrently locally.

In LOCAL mode, this takes 10 seconds to run. This is because we delegate all work to the microservices - and they
respond to the work synchronously.

This sounds worse, but is actually desired - the sleeps simulate difficult work, so for the following tasks:
 - 10x 1 second
 - 3x 3 second
 - 1x 5 second

The the effective load on the various services is as follows:
  ZERO: main(24 seconds)
  LOCAL: main(0 seconds), sleep_1(10 seconds), sleep_3(9 seconds), sleep_5(5 seconds)
"""

import time

from threading import Thread, active_count

from microservice.core.service_waypost import init_service_waypost

from microservice.examples.sleepers import sleep_1, sleep_3, sleep_5


if __name__ == "__main__":
    init_service_waypost()

    thread_results = []


    def result_collator(func):
        def wrapper():
            thread_results.append(func())
        return wrapper


    funcs_to_run = [sleep_1, sleep_1, sleep_1, sleep_1, sleep_1, sleep_1, sleep_1, sleep_1, sleep_1, sleep_1,
                    sleep_3, sleep_3, sleep_3,
                    sleep_5]

    threads = []
    for func in funcs_to_run:
        new_thread = Thread(target=result_collator(func))
        new_thread.start()
        threads.append(new_thread)

    while active_count() > 1:
        print(thread_results)
        time.sleep(0.2)

    for thread in threads:
        thread.join()

    print(thread_results)
