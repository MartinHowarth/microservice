import os
import threading
import time


class _HealthChecker:
    @property
    def heartbeat_response(self):
        return {
            'percent_idle': self.percent_idle,
        }

    @property
    def percent_idle(self):
        return 1


class _TimeBasedHealthChecker(_HealthChecker):
    stats_roll_period = 5
    stats_interval = 1

    def __init__(self):
        self.running = True

        # Values for calculation percent idle
        self.avg_percent_idle = 1
        self._last_os_time = 0
        self._avg_idle_thread = threading.Thread(target=self._calculate_avg_percent_idle)
        self._avg_idle_thread.start()

    def __del__(self):
        self.running = False
        self._avg_idle_thread.join(timeout=0)

    @property
    def percent_idle(self):
        return self.avg_percent_idle

    @property
    def _percent_idle(self):
        this_cycle = os.times()[0]
        diff = this_cycle - self._last_os_time
        self._last_os_time = this_cycle

        last_idle_time = 1 - (diff / self.stats_interval)
        return last_idle_time

    def _calculate_avg_percent_idle(self):
        while self.running:
            total = 0
            for i in range(0, self.stats_roll_period, self.stats_interval):
                total += self._percent_idle
                time.sleep(self.stats_interval)
            self.avg_percent_idle = total / (self.stats_roll_period / self.stats_interval)
            print("Average percent idle is:", self.avg_percent_idle)


HealthChecker = _TimeBasedHealthChecker()
