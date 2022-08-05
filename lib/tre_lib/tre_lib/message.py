#!/usr/bin/env python3
"""
Module to define class to represent a message.
"""
import logging
import uuid
import json
import os
import time

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
    MESSAGE_VERSION = '1.0.0'
    KEY_VERSION = 'version'
    KEY_TIMESTAMP = 'timestamp'
    KEY_UUIDS = 'UUIDs'
    UUID_KEY_SUFFIX = '-UUID'
    KEY_PRODUCER = 'producer'
    KEY_NAME = 'name'
    KEY_PROCESS = 'process'
    KEY_TYPE = 'type'
    KEY_ENVIRONMENT = 'environment'
    KEY_PARAMETERS = 'parameters'

    def validate(
        self,
        producer: str,
        process: str,
        type: str,
        environment: str,
        parameters: dict = None,
        prior_message: dict = None
    ):
        """
        Raise error if input parameters are invalid.
        """
        logger.info('validate')
        if producer is None or len(producer) == 0:
            raise ValueError('Empty "producer" argument')
        elif process is None or len(process) == 0:
            raise ValueError('Empty "process" argument')
        elif type is None or len(type) == 0:
            raise ValueError('Empty "type" argument')
        elif environment is None or len(environment) == 0:
            raise ValueError('Empty "environment" argument')
        elif parameters is not None and not isinstance(parameters, dict):
            raise ValueError(f'parameters is not dict type')
        elif prior_message is not None:
            if not isinstance(prior_message, dict):
                raise ValueError(f'prior_message is not dict type')
            elif self.KEY_UUIDS not in prior_message:
                raise ValueError(f'No key "{self.KEY_UUIDS}" in prior_message')
            elif not isinstance(prior_message[self.KEY_UUIDS], list):
                raise ValueError(
                    f'Key "{self.KEY_UUIDS}" in prior_message is not list type')

    def __init__(
            self,
            producer: str,
            process: str,
            type: str,
            environment: str,
            parameters: dict = None,
            prior_message: dict = None,
            timestamp_ns_utc: int = None
    ):
        """
        Validate input, initialise new message object.

        Arguments:
        producer: The system name for the message; e.g. "TRE", "TDR", etc
        process: The name of the process that will send the message
        type: The type of the consignment; e.g. "judgment", "standard"
        environment: The execution environment; e.g. "dev", "test", "int", etc
        parameters: The (dict) content for this message's parameters section
        prior_message: An (optional) input message dict with UUID history
        """
        logger.info('__init__')
        self.validate(
            producer=producer, process=process, type=type,
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

        self.new_message[self.KEY_UUIDS].append({self.uuid_key: self.uuid})
        self.new_message[self.KEY_PRODUCER] = {}
        self.new_message[self.KEY_PRODUCER][self.KEY_NAME] = producer
        self.new_message[self.KEY_PRODUCER][self.KEY_PROCESS] = process
        self.new_message[self.KEY_PRODUCER][self.KEY_TYPE] = type
        self.new_message[self.KEY_PRODUCER][self.KEY_ENVIRONMENT] = environment

        if parameters is None:
            self.new_message[self.KEY_PARAMETERS] = {}
        else:
            self.new_message[self.KEY_PARAMETERS] = parameters

    def to_json_str(self, indent=None) -> str:
        return json.dumps(self.new_message)

    def to_dict(self) -> dict:
        return self.new_message


if __name__ == "__main__":
    setup_logging()
