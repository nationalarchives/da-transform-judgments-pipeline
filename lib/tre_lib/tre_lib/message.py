#!/usr/bin/env python3
"""
Module to define class to represent a message.
"""
import logging
import uuid
import json
import os
import time
import pkgutil
from jsonschema import validate

logger = logging.getLogger(__name__)


def setup_logging(
    default_config_file='logging.json',
    default_level=logging.INFO,
    log_config_env_key='LOG_CONFIG_JSON'
):
    env_key_path = os.getenv(log_config_env_key, None)
    config_file = env_key_path if env_key_path else default_config_file
    if os.path.exists(config_file):
        with open(config_file, 'rt') as f:
            logging.config.dictConfig(json.load(f.read()))
    else:
        format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(level=default_level, format=format_str)


class Message():
    """
    Represents a message payload.
    """
    MESSAGE_VERSION = '0.0.2'
    KEY_VERSION = 'version'
    KEY_TIMESTAMP = 'timestamp'
    KEY_UUIDS = 'UUIDs'
    UUID_KEY_SUFFIX = '-UUID'
    KEY_PRODUCER = 'producer'
    KEY_NAME = 'name'
    KEY_PROCESS = 'process'
    KEY_TYPE = 'type'
    KEY_EVENT_NAME = 'event-name'
    KEY_ENVIRONMENT = 'environment'
    KEY_PARAMETERS = 'parameters'

    @staticmethod
    def get_schema(schema_name: str = 'schema.json'):
        return json.loads(
            pkgutil.get_data(
                package=__name__,
                resource=schema_name
            ).decode()
        )

    def validate_input(
        self,
        environment: str,
        producer: str,
        process: str,
        event_name: str,
        parameters: dict = None,
        prior_message: dict = None
    ):
        """
        Raise error if input parameters are invalid.
        """
        logger.info('validate')
        logger.info(f'prior_message={prior_message}')
        if not environment:
            raise ValueError('Empty "environment" argument')
        elif not producer:
            raise ValueError('Empty "producer" argument')
        elif not process:
            raise ValueError('Empty "process" argument')
        elif not event_name:
            raise ValueError('Empty "event_name" argument')
        elif parameters and not isinstance(parameters, dict):
            raise ValueError(f'parameters is not dict type')
        elif prior_message is not None:
            validate(instance=prior_message,
                     schema=Message.get_schema())

    def __init__(
            self,
            environment: str,
            producer: str,
            process: str,
            event_name: str,
            parameters: dict = None,
            type: str = None,
            prior_message: dict = None,
            timestamp_ns_utc: int = None
    ):
        """
        Validate input, initialise new message object.

        environment: str
            The execution environment; e.g. "dev", "test", "int", etc
        producer: str
            The system name for the message; e.g. "TRE", "TDR", etc
        process: str
            The name of the process that will send the message
        event_name: str
            The name of the event that is occurring and will be sent; e.g.
            "bagit-validated", "bagit-export", etc
        parameters: dict
            The content for this message's parameters section
        type: str
            Optional consignment type (e.g. "judgment", "standard"); overrides
            default value from prior_message (if present)
        prior_message: dict
            Optional input message dict (with UUID history parameter, type
            parameter, etc)
        timestamp_ns_utc: int
            Optional alternate timestamp value (nanoseconds UTC)
        """
        logger.info('__init__')
        self.validate_input(
            producer=producer, process=process, event_name=event_name,
            environment=environment, parameters=parameters,
            prior_message=prior_message)

        if timestamp_ns_utc is None:
            timestamp_ns_utc = time.time_ns()

        # Create new UUID and corresponding key name (with producer name)
        self.uuid_key = f'{producer}{self.UUID_KEY_SUFFIX}'
        self.uuid = str(uuid.uuid4())
        logger.info(f'self.uuid_key={self.uuid_key} self.uuid={self.uuid}')

        self.new_message = {}
        self.new_message[self.KEY_VERSION] = self.MESSAGE_VERSION
        self.new_message[self.KEY_TIMESTAMP] = timestamp_ns_utc

        if prior_message is None:
            self.new_message[self.KEY_UUIDS] = []
        else:
            # Use [:] to copy (not reference) prior UUIDs
            self.new_message[self.KEY_UUIDS] = prior_message[self.KEY_UUIDS][:]
            self.new_message[self.KEY_UUIDS] = prior_message[self.KEY_UUIDS][:]

        self.new_message[self.KEY_UUIDS].append({self.uuid_key: self.uuid})

        self.new_message[self.KEY_PRODUCER] = {}
        self.new_message[self.KEY_PRODUCER][self.KEY_ENVIRONMENT] = environment
        self.new_message[self.KEY_PRODUCER][self.KEY_NAME] = producer
        self.new_message[self.KEY_PRODUCER][self.KEY_PROCESS] = process
        self.new_message[self.KEY_PRODUCER][self.KEY_EVENT_NAME] = event_name

        # Default to type of prior_message, but type parameter overrides it
        if type:
            self.new_message[self.KEY_PRODUCER][self.KEY_TYPE] = type
        elif prior_message and (self.KEY_TYPE in prior_message):
            prior_type = prior_message[self.KEY_TYPE]
            self.new_message[self.KEY_PRODUCER][self.KEY_TYPE] = prior_type
        else:
            self.new_message[self.KEY_PRODUCER][self.KEY_TYPE] = None

        if parameters is None:
            self.new_message[self.KEY_PARAMETERS] = {}
        else:
            self.new_message[self.KEY_PARAMETERS] = parameters

    def to_json_str(self, indent=None) -> str:
        return json.dumps(self.new_message, indent=indent)

    def to_dict(self) -> dict:
        return self.new_message


if __name__ == "__main__":
    setup_logging(default_level=logging.INFO)
