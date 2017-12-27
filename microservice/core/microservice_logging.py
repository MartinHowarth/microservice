import json
import logging
import msgpack
import random
import sys

from io import BytesIO
from fluent import asynchandler as handler
from logstash_async.handler import AsynchronousLogstashHandler
from logstash_formatter import LogstashFormatterV1

from microservice.core import settings


def overflow_handler(pendings):
    """
    Method for dealing with fluentd events that overflowed the buffer and failed to send to
    fluentd. Also called for all outstanding events when software is closed.

    :param pendings:
    """
    unpacker = msgpack.Unpacker(BytesIO(pendings))
    for unpacked in unpacker:
        print("Fluentd overflow: {}".format(unpacked))


class RequestIDLogFilter(logging.Filter):
    """
    Log filter to inject the current request id of the request under `log_record.request_id`
    """

    def filter(self, log_record):
        log_record.request_id = settings.current_request_id()
        return log_record


class HumanReadableLogstashFormatter(LogstashFormatterV1):
    """
    Convert the json formatted logstash logs to more standard human-readable logs for stdout consumption.

    This allows using the `extra={}` kwarg in logging statements for the LogstashFormatter, while also making sure that
    gets formatting into the message correctly.
    """
    def format(self, record):
        logstash_formatted = super(HumanReadableLogstashFormatter, self).format(record)
        data = json.loads(logstash_formatted)
        ret = "{@timestamp} {levelname}\t{instance_id}-{request_id}: {message}".format(
            **data
        )
        if data['stack_info']:
            ret += " " + data['stack_info']
        return ret


def configure_logging(service_name):
    """
    Configure logging based on the settings in the settings file.
    This sets up a handler for each logging mode that is enabled.
    See `microservice.core.settings.LoggingMode` for the supported logging types.

    :param str service_name: Name of the service being served by this instance.
    """
    logger = logging.getLogger()
    logger.setLevel(settings.logging_level)

    formatter_kwargs = {
        'fmt': json.dumps({'extra': {
            'local_service': service_name,
            # Basic way to distinguish logs between instances of the same microservice.
            'instance_id': random.randint(100000, 999999)
        }})
    }

    formatter = LogstashFormatterV1(**formatter_kwargs)

    if settings.LoggingMode.FILE in settings.logging_modes:
        file_handler = logging.FileHandler('{}.log'.format(service_name))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIDLogFilter())
        logger.addHandler(file_handler)

    if settings.LoggingMode.HUMAN in settings.logging_modes:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(HumanReadableLogstashFormatter(**formatter_kwargs))
        stdout_handler.addFilter(RequestIDLogFilter())
        logger.addHandler(stdout_handler)

    if settings.LoggingMode.STDOUT in settings.logging_modes:
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        stdout_handler.addFilter(RequestIDLogFilter())
        logger.addHandler(stdout_handler)

    if settings.LoggingMode.LOGSTASH in settings.logging_modes:
        # TODO: test this
        raise Exception("Warning: untested")
        logstash_handler = AsynchronousLogstashHandler(
            **settings.logstash_settings)
        logstash_handler.setFormatter(formatter)
        logstash_handler.addFilter(RequestIDLogFilter())
        logger.addHandler(logstash_handler)

    if settings.LoggingMode.FLUENTD in settings.logging_modes:
        # TODO: test this
        raise Exception("Warning: untested")
        fluentd_handler = handler.FluentHandler(
            'pycroservices.follow',
            **settings.fluentd_settings,
            buffer_overflow_handler=overflow_handler)
        fluentd_handler.setFormatter(formatter)
        fluentd_handler.addFilter(RequestIDLogFilter())
        logger.addHandler(fluentd_handler)
