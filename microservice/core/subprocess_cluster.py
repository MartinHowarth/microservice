import os
import platform
import psutil
import requests
import subprocess
import threading
import time

from collections import namedtuple
from flask import Flask, request
from setuptools import Distribution
from setuptools.command.install import install
from typing import List, Dict

from microservice.core import settings
from microservice.core.microservice_cluster import MicroserviceCluster

DETACHED_PROCESS = 8


class OnlyGetScriptPath(install):
    def run(self):
        # does not call install.run() by design
        self.distribution.install_scripts = self.install_scripts


def get_setuptools_script_dir():
    """
    Find where setuptools will have installed the `microservice` entrypoint executable to.
    :return: Path to the setuptools script directory.
    """
    dist = Distribution({'cmdclass': {'install': OnlyGetScriptPath}})
    dist.dry_run = True  # not sure if necessary, but to be safe
    dist.parse_config_files()
    command = dist.get_command_obj('install')
    command.ensure_finalized()
    command.run()
    return dist.install_scripts


def is_windows():
    return platform.system().lower() == 'windows'


def get_microservice_main_entrypoint_path():
    """
    Get the platform-dependent microservice main entrypoint path. This is so that we can call the `microservice`
    entrypoint as setup by `setup.py`.

    :return: The path to the main entrypoint of the microservice package.
    """
    # TODO: This doesn't support virtualenvs
    if is_windows():
        return os.path.join(get_setuptools_script_dir(), 'microservice.exe')
    else:
        return os.path.join(get_setuptools_script_dir(), 'microservice')


SubprocessService = namedtuple("SubprocessService", ['process', 'host', 'port'])


def spawn_microservice(service_name, host, port):
    cmd = [get_microservice_main_entrypoint_path(),
           "--host", str(host),
           "--port", str(port),
           "--service", service_name]
    if is_windows():
        return subprocess.Popen(cmd, creationflags=DETACHED_PROCESS, close_fds=True)
    else:
        # todo: test on linux
        return subprocess.Popen(cmd, start_new_session=True, close_fds=True)


def uri_from_subprocess_service(subprocess_service):
    return "http://{}:{}/".format(subprocess_service.host, subprocess_service.port)


class SubprocessMicroserviceCluster(MicroserviceCluster):
    deployment_mode = settings.DeploymentMode.SUBPROCESS
    next_port = 10000

    deployment_manager_host = '127.0.0.1'
    deployment_manager_port = 9999

    def __init__(self, *args, **kwargs):
        super(SubprocessMicroserviceCluster, self).__init__(*args, **kwargs)
        self.host = "127.0.0.1"
        self.services = {}  # type: Dict[str, SubprocessService]
        self.deployment_manager_thread = None

        self.deployment_manager_uri = 'http://{}:{}/'.format(self.deployment_manager_host, self.deployment_manager_port)

    def setup(self):
        super(SubprocessMicroserviceCluster, self).setup()
        self.create_deployment_manager()
        self.set_deployment_manager_uri()

    def teardown(self):
        super(SubprocessMicroserviceCluster, self).teardown()
        requests.get(self.deployment_manager_uri + 'terminate')
        self.deployment_manager_thread.join()

    def create_deployment_manager(self):
        app = Flask(__name__)

        @app.route('/uri/<service_name>')
        def uri_for_service(service_name):
            return self.uri_for_service(service_name)

        @app.route('/terminate')
        def terminate():
            """
            Trigger this flask app to terminate.
            """
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
            return "Server shutting down..."

        self.deployment_manager_thread = threading.Thread(
            target=app.run,
            kwargs={'host': self.deployment_manager_host, 'port': self.deployment_manager_port})
        self.deployment_manager_thread.start()

    def set_deployment_manager_uri(self):
        self.send_request_to_all_services('deployment_manager_uri',
                                          data={'deployment_manager_uri': self.deployment_manager_uri},
                                          method=requests.post)

    def uri_for_service(self, service_name):
        return uri_from_subprocess_service(self.services[service_name])

    def spawn_all_microservices(self):
        for service_name in self.service_names:
            port = self.next_port
            self.next_port += 1
            process = spawn_microservice(service_name, self.host, port)
            self.services[service_name] = SubprocessService(process, self.host, port)

        # Sleep to allow the microservices to initialise. Could be replaced with an active poller, but not worth the
        # effort for the test-only subprocess deployment.
        time.sleep(1)

    def close_all_microservices(self):
        for service in self.services.values():
            process = psutil.Process(service.process.pid)
            for proc in process.children(recursive=True):
                proc.kill()
            process.kill()

    def all_microservices_are_alive(self):
        results = self.send_request_to_all_services('ping')
        return all([res.text == "pong" for res in results.values()])
