import atexit
import subprocess
import time

DETACHED_PROCESS = 8

orchestrator_cmd = "microservice --orchestrator".split(' ')
all_processes = []


# TODO: This doesn't actually work by default on windows because we don't have permission to kill the detached processes
@atexit.register
def kill_subprocesses():
    for proc in all_processes:
        print("killing", proc)
        proc.kill()


def main():
    print("starting")
    # The DETACHED_PROCESS option means we no longer have authority to kill it again by default. However, it is the
    # only option as it creates entirely detached subprocesses which is required for robustness/scaling/nice things.
    # orchestrator = subprocess.Popen(orchestrator_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    orchestrator = subprocess.Popen(orchestrator_cmd, creationflags=DETACHED_PROCESS, close_fds=True)
    # orchestrator = subprocess.Popen(orchestrator_cmd)
    print("orchestrator up")
    all_processes.append(orchestrator)
    # Allow time for process to setup/detach fully before we quit.
    time.sleep(2)
    # input("exit?")


if __name__ == "__main__":
    main()
