#!/usr/bin/env python3
"""
Invoke the Step Function ARN in environment variable TRE_STATE_MACHINE_ARN
once for each TRE event in the incoming AWS event.

A maximum of 10 events are expected as this is the current limit when using a
batch_window of 0 seconds; see:

https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html

Environment variables:

TRE_STATE_MACHINE_ARN    : The ARN of the Step Function to execute
TRE_CONSIGNMENT_KEY_PATH : Dot separated path to locate the consignment
                           reference field in the events being forwarded (the
                           consignment reference is used in the Step Function
                           execution name)
"""
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
HTTP_OK_STATUS_CODES = [200]

client = boto3.client('stepfunctions')


def get_dict_key_value(source: dict, key_path: list):
    """
    Get the value of the key in `dict` identified by navigating the key values
    in the `key_path` in reverse order.
    """
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


def get_latest_uuid(tre_event: dict) -> str:
    """
    Returns the TRE event's latest UUID.
    """
    if KEY_UUIDS in tre_event:
        uuid_list = tre_event[KEY_UUIDS]
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


class TREStepFunctionExecutionError(Exception):
    """
    For step function execution errors.
    """


def execute_step_function(
    step_function_arn: str,
    event_record: dict
):
    """
    Execute the specified step_function_arn with the TRE event payload
    extracted from `event_record`. Contextual information (such as event UUID)
    is used for the execution instance name.

    On success a status dictionary with the following structure is returned:

    {
        'uuid': "...",
        'response': { ... }
    }

    If the execution does not return a 200 OK HTTP status code, a
    TREStepFunctionExecutionError error is raised.
    """
    logger.info('step_function_arn=%s', step_function_arn)
    logger.info('event_record=%s', event_record)

    # Extract TRE message
    logger.info('event_record: %s', event_record)
    event_record_body = json.loads(event_record['body'])
    logger.info('event_record_body: %s', event_record_body)
    tre_message = json.loads(event_record_body['Message'])
    logger.info('tre_message: %s', tre_message)

    # Get consignment reference for the execution name
    cr_keys = list(reversed(TRE_CONSIGNMENT_KEY_PATH.split(PATH_SEPARATOR)))
    logger.info('cr_keys=%s', cr_keys)
    consignment_ref = get_dict_key_value(source=tre_message, key_path=cr_keys)
    logger.info('consignment_ref=%s', consignment_ref)
    if consignment_ref is None:
        consignment_ref = UNKNOWN_VALUE

    # Get event source (SQS queue name) for the execution name
    event_source = UNKNOWN_VALUE
    if EVENT_SOURCE_ARN in event_record:
        arn = event_record[EVENT_SOURCE_ARN]
        event_source = arn.split(':')[5]

    # Get latest message UUID for the execution name
    latest_uuid = get_latest_uuid(tre_event=tre_message)
    logger.info('latest_uuid=%s', latest_uuid)

    # Build execution name
    name_list = [consignment_ref, event_source, latest_uuid]
    logger.info('name_list=%s', name_list)
    execution_name = NAME_SEPARATOR.join(name_list)
    logger.info('execution_name=%s', execution_name)

    # Invoke Step Function and output start response message
    execution_response = client.start_execution(
        stateMachineArn=TRE_STATE_MACHINE_ARN,
        name=execution_name,
        input=json.dumps(tre_message)
    )

    logger.info(f'execution_response={execution_response}')

    # This implies 200 is the only expected non-error response code:
    # https://docs.aws.amazon.com/step-functions/latest/apireference/API_StartExecution.html
    http_code = int(execution_response['ResponseMetadata']['HTTPStatusCode'])
    if http_code not in HTTP_OK_STATUS_CODES:
        error_message = (
            f'Event UUID {latest_uuid} Step Function start_execution response '
            f'is {execution_response}'
        )

        logging.error(error_message)
        raise TREStepFunctionExecutionError(error_message)
    
    # Execution was OK, return event's UUID and step function execution response
    return {
        'uuid': latest_uuid,
        'response': execution_response
    }


def handler(event, context):
    """
    AWS invocation entry point.
    """
    logger.info('TRE_STATE_MACHINE_ARN=%s', TRE_STATE_MACHINE_ARN)
    logger.info('TRE_CONSIGNMENT_KEY_PATH=%s', TRE_CONSIGNMENT_KEY_PATH)
    logger.info('event=%s', event)

    if KEY_RECORDS not in event:
        raise ValueError(f'Missing key "{KEY_RECORDS}"')

    # Iterate over supplied records; may receive > 1
    execution_fail_list = []
    execution_ok_list = []
    for event_record in event[KEY_RECORDS]:
        try:
            execution_info = execute_step_function(
                step_function_arn=TRE_STATE_MACHINE_ARN,
                event_record=event_record
            )

            execution_ok_list.append(execution_info)
        except Exception as e:
            logging.exception(e, stack_info=True)
            execution_fail_list.append(
                {
                    'event_record': event_record,
                    'error': str(e)
                }
            )

    # Raise an error if there were any failed executions
    if len(execution_fail_list) > 0:
        logger.error('Error processing events: %s', execution_fail_list)
        raise TREStepFunctionExecutionError(
            f'Failed to process {len(execution_fail_list)}/'
            f'{len(event[KEY_RECORDS])} events; see log for details'
        )

    # Completed OK, return details of any step function execution(s)
    logger.info('Completed OK; execution_ok_list=%s', execution_ok_list)
    return execution_ok_list
