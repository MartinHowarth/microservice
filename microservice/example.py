import atexit
import subprocess

DETACHED_PROCESS = 8

orchestrator_cmd = "microservice --orchestrator".split(' ')
echos_cmd = "microservice --local_services microservice.development.functions.echo_as_dict,microservice.development.functions.echo_as_dict2".split(' ')
all_processes = []


@atexit.register
def kill_subprocesses():
    for proc in all_processes:
        print("killing", proc)
        proc.kill()


def main():
    print("starting")
    # orchestrator = subprocess.Popen(orchestrator_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    orchestrator = subprocess.Popen(orchestrator_cmd, creationflags=DETACHED_PROCESS, close_fds=True)
    # orchestrator = subprocess.Popen(orchestrator_cmd)
    print("orchestrator up")
    # echos = subprocess.run(echos_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # echos = subprocess.Popen(echos_cmd, creationflags=DETACHED_PROCESS, close_fds=True)
    # echos = subprocess.Popen(echos_cmd)
    print("echos up")
    all_processes.append(orchestrator)
    # all_processes.append(echos)
    input("enter to exit")


if __name__ == "__main__":
    main()
