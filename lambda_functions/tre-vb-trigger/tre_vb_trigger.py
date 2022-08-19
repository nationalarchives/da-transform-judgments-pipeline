#!/usr/bin/env python3
import logging
import json
import boto3
import os

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PATH_SEPARATOR = '.'
NAME_SEPARATOR = '-'
UNKNOWN_VALUE = '_'
EVENT_SOURCE_ARN = 'eventSourceARN'
KEY_RECORDS = 'Records'
KEY_UUIDS = 'UUIDs'
TRE_STATE_MACHINE_ARN = os.environ['TRE_STATE_MACHINE_ARN']
TRE_CONSIGNMENT_KEY_PATH = os.environ['TRE_CONSIGNMENT_KEY_PATH']
TRE_RETRY_KEY_PATH = os.environ['TRE_RETRY_KEY_PATH']

client = boto3.client('stepfunctions')


def get_dict_key_value(source: dict, key_path: list):
    logger.debug(f'get_dict_key_value start: key_path={key_path}')
    current_search_key = key_path.pop()

    for source_key in source:
        if source_key == current_search_key:  # found matching current key
            if len(key_path) == 0:  # nothing else to find, return result
                return source[source_key]
            elif type(source[source_key]) is dict:
                return get_dict_key_value(source=source[source_key],
                                          key_path=key_path)
            else:  # still keys to find, but no records to search
                return None


def get_latest_uuid(tre_message: dict) -> str:
    if KEY_UUIDS in tre_message:
        uuid_list = tre_message[KEY_UUIDS]
        if isinstance(uuid_list, list):
            if len(uuid_list) > 0:
                latest_uuid_dict = uuid_list[-1]
                key_count = len(latest_uuid_dict.keys())
                if key_count == 1:
                    uuid_key = list(latest_uuid_dict.keys())[0]
                    return latest_uuid_dict[uuid_key]
                else:
                    raise ValueError(f'UUID key count is {key_count}, not 1')
            else:
                raise ValueError(f'Key "{KEY_UUIDS}" is an empty list')
        else:
            raise ValueError(f'Key "{KEY_UUIDS}" is not a list')
    else:
        raise ValueError(f'Missing key "{KEY_UUIDS}"')


def handler(event, context):
    logger.info(f'TRE_STATE_MACHINE_ARN={TRE_STATE_MACHINE_ARN}')
    logger.info(f'TRE_CONSIGNMENT_KEY_PATH={TRE_CONSIGNMENT_KEY_PATH}')
    logger.info(f'TRE_RETRY_KEY_PATH={TRE_RETRY_KEY_PATH}')
    logger.info(f'event:\n{event}')

    if KEY_RECORDS not in event:
        raise ValueError(f'Missing key "{KEY_RECORDS}"')

    # If >1 record, fail here so don't silently ignore unexpected records
    records_count = len(event[KEY_RECORDS])
    if records_count != 1:
        raise ValueError(f'Expected 1 record, got {records_count}')

    # Extract TRE message
    event_record = event[KEY_RECORDS][0]
    logger.info(f'event_record:\n{event_record}')
    event_record_body = json.loads(event_record['body'])
    logger.info(f'event_record_body:\n{event_record_body}')
    tre_message = json.loads(event_record_body['Message'])
    logger.info(f'tre_message:\n{tre_message}')

    # Get consignment reference for the execution name
    cr_keys = list(reversed(TRE_CONSIGNMENT_KEY_PATH.split(PATH_SEPARATOR)))
    logger.info(f'cr_keys={cr_keys}')
    consignment_ref = get_dict_key_value(source=tre_message, key_path=cr_keys)
    logger.info(f'consignment_ref={consignment_ref}')
    if consignment_ref is None:
        consignment_ref = UNKNOWN_VALUE

    # Get retry number for the execution name
    retry_keys = list(reversed(TRE_RETRY_KEY_PATH.split(PATH_SEPARATOR)))
    logger.info(f'retry_keys={retry_keys}')
    retry_number = get_dict_key_value(source=tre_message, key_path=retry_keys)
    logger.info(f'retry_number={retry_number}')
    if retry_number is None:
        retry_number = UNKNOWN_VALUE

    # Get event source (SQS queue name) for the execution name
    event_source = UNKNOWN_VALUE
    if EVENT_SOURCE_ARN in event_record:
        arn = event_record[EVENT_SOURCE_ARN]
        event_source = arn.split(':')[5]

    # Get latest message UUID for the execution name
    latest_uuid = get_latest_uuid(tre_message=tre_message)
    logger.info(f'latest_uuid={latest_uuid}')

    # Build execution name
    name_list = [consignment_ref, str(retry_number), event_source, latest_uuid]
    logger.info(f'name_list={name_list}')
    execution_name = NAME_SEPARATOR.join(name_list)
    logger.info(f'execution_name={execution_name}')

    # Invoke Step Function and output start response message
    start_execution_response = client.start_execution(
        stateMachineArn=TRE_STATE_MACHINE_ARN,
        name=execution_name,
        input=json.dumps(tre_message)
    )

    logger.info(f'start_execution_response={start_execution_response}')
