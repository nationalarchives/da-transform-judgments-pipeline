#!/usr/bin/env python3
"""
Module to test TRE message code.

Run from this directory with: python3 -m unittest
"""
import unittest
from message import Message
import json
import uuid
import logging
import os


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


class TestMessage(unittest.TestCase):
    MSG_NOT_EXPECTED_ERR = 'Did not get expected error message'
    PRODUCER = 'TRE'
    TYPE_JUDGMENT='Judgment'
    TYPE_STANDARD='Standard'

    def test_minimal_ok(self):
        PROCESS = 'test_str_output process'
        TYPE = 'test_str_output type'
        ENVIRONMENT = 'test_str_output environment'

        tre_message = Message(
            producer=self.PRODUCER,
            process=PROCESS,
            type=TYPE,
            environment=ENVIRONMENT)

        json_output = json.loads(tre_message.to_json_str())
        logging.info(json.dumps(json_output, indent=2))

        # Ensure top-level keys are present
        self.assertTrue(
            Message.KEY_VERSION in json_output,
            f'Key "{Message.KEY_VERSION}" not found')

        self.assertTrue(
            Message.KEY_TIMESTAMP in json_output,
            f'Key "{Message.KEY_TIMESTAMP}" not found')

        self.assertTrue(
            Message.KEY_UUIDS in json_output,
            f'Key "{Message.KEY_UUIDS}" not found')

        self.assertTrue(
            Message.KEY_PRODUCER in json_output,
            f'Key "{Message.KEY_PRODUCER}" not found')

        self.assertTrue(
            Message.KEY_PARAMETERS in json_output,
            f'Key "{Message.KEY_PARAMETERS}" not found')

        # Ensure producer child keys are present
        self.assertTrue(
            Message.KEY_NAME in json_output[Message.KEY_PRODUCER],
            f'Key "{Message.KEY_NAME}" not found under key "{Message.KEY_PRODUCER}"')

        self.assertTrue(
            Message.KEY_PROCESS in json_output[Message.KEY_PRODUCER],
            f'Key "{Message.KEY_PROCESS}" not found under key "{Message.KEY_PRODUCER}"')

        self.assertTrue(
            Message.KEY_TYPE in json_output[Message.KEY_PRODUCER],
            f'Key "{Message.KEY_TYPE}" not found under key "{Message.KEY_PRODUCER}"')

        self.assertTrue(
            Message.KEY_ENVIRONMENT in json_output[Message.KEY_PRODUCER],
            f'Key "{Message.KEY_ENVIRONMENT}" not found under key "{Message.KEY_PRODUCER}"')

        # Ensure a valid UUID was generated and is present in the UUIDs list
        try:
            uuid.UUID(tre_message.uuid, version=4)
        except ValueError as e:
            self.fail(f'Generated UUID "{tre_message.uuid}" is not valid: {e}')

        self.assertTrue(
            tre_message.uuid in [
                u[f'{self.PRODUCER}-UUID']
                for u in json_output[Message.KEY_UUIDS]
            ],
            f'Key "{tre_message.uuid}" not found in UUID list')

        # Ensure expected output values set
        self.assertTrue(
            json_output[Message.KEY_PRODUCER][Message.KEY_NAME] == self.PRODUCER,
            f'Key "{Message.KEY_PRODUCER}.{Message.KEY_NAME}" has invalid value')

        self.assertTrue(
            json_output[Message.KEY_PRODUCER][Message.KEY_PROCESS] == PROCESS,
            f'Key "{Message.KEY_PRODUCER}.{Message.KEY_PROCESS}" has invalid value')

        self.assertTrue(
            json_output[Message.KEY_PRODUCER][Message.KEY_TYPE] == TYPE,
            f'Key "{Message.KEY_PRODUCER}.{Message.KEY_TYPE}" has invalid value')

        self.assertTrue(
            json_output[Message.KEY_PRODUCER][Message.KEY_ENVIRONMENT] == ENVIRONMENT,
            f'Key "{Message.KEY_PRODUCER}.{Message.KEY_ENVIRONMENT}" has invalid value')

    def test_process_none(self):
        try:
            Message(
                producer=self.PRODUCER,
                process=None,
                type='t',
                environment='e')
            self.fail('No ValueError with missing process argument')
        except ValueError as e:
            self.assertTrue(
                str(e) == 'Empty "process" argument',
                self.MSG_NOT_EXPECTED_ERR)

    def test_process_empty(self):
        try:
            Message(
                producer=self.PRODUCER,
                process='',
                type='t',
                environment='e')
            self.fail('No ValueError with empty process argument')
        except ValueError as e:
            self.assertTrue(
                str(e) == 'Empty "process" argument',
                self.MSG_NOT_EXPECTED_ERR)

    def test_no_type_is_allowed(self):
        Message(
            producer=self.PRODUCER,
            process='p',
            type=None,
            environment='e')

        Message(
            producer=self.PRODUCER,
            process='p',
            type='',
            environment='e')

    def test_environment_none(self):
        try:
            Message(
                producer=self.PRODUCER,
                process='p',
                type='t',
                environment=None)
            self.fail('No ValueError with missing environment argument')
        except ValueError as e:
            self.assertTrue(
                str(e) == 'Empty "environment" argument',
                self.MSG_NOT_EXPECTED_ERR)

    def test_environment_empty(self):
        try:
            Message(
                producer=self.PRODUCER,
                process='p',
                type='t',
                environment='')
            self.fail('No ValueError with empty environment argument')
        except ValueError as e:
            self.assertTrue(
                str(e) == 'Empty "environment" argument',
                self.MSG_NOT_EXPECTED_ERR)

    def test_uuid_accumulation(self):
        PRODUCER_1 = 'p1'
        PRODUCER_2 = 'p2'
        PROCESS_PREFIX = 'uk.gov.nationalarchives.test.producer'
        PROCESS_1 = f'{PROCESS_PREFIX}1'
        PROCESS_2 = f'{PROCESS_PREFIX}2'
        TYPE = self.TYPE_JUDGMENT
        ENVIRONMENT = 'unit-test'

        m1 = Message(
            producer=PRODUCER_1,
            process=PROCESS_1,
            type=TYPE,
            environment=ENVIRONMENT)

        self.assertTrue(len(m1.new_message[Message.KEY_UUIDS]) == 1,
                        'm1 UUIDs list len is not 1')
        m1j = json.loads(m1.to_json_str())
        logging.info(json.dumps(m1j, indent=2))

        m2 = Message(
            producer=PRODUCER_2,
            process=PROCESS_2,
            type=TYPE,
            environment=ENVIRONMENT,
            prior_message=m1.to_dict())

        m1j = json.loads(m1.to_json_str())
        logging.info(json.dumps(m1j, indent=2))
        self.assertTrue(len(m1.new_message[Message.KEY_UUIDS]) == 1,
                        'm1 UUIDs list len is not 1')
        m2j = json.loads(m2.to_json_str())
        logging.info(json.dumps(m2j, indent=2))
        self.assertTrue(len(m2.new_message[Message.KEY_UUIDS]) == 2,
                        'm2 UUIDs list len is not 2')


setup_logging(default_level=logging.INFO)
