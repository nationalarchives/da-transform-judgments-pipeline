"""
Forward TRE events in the AWS input `event` to the SNS topic specified in
environment variable TRE_OUT_TOPIC_ARN. AWS MessageAttributes (that typically
mirror TRE event producer attributes, for subsequent filtering) are also
forwarded.
"""
import boto3
import json
import os
import logging

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sns = boto3.client('sns')
TRE_OUT_TOPIC_ARN = os.environ['TRE_OUT_TOPIC_ARN']

KEY_RECORDS = 'Records'
KEY_BODY = 'body'
KEY_MESSAGE = 'Message'
KEY_MESSAGE_ATTRIBUTES = 'MessageAttributes'
KEY_EVENT_RECORD = 'event_record'
KEY_ERROR = 'error'
HTTP_OK_STATUS_CODES = [200]


class TREEventForwardError(Exception):
    """
    For event forward errors.
    """


def forward_tre_event_to_sns(
    event_record: dict,
    target_sns_arn: str
):
    """
    Forward the TRE event in `event_record` to `target_sns_arn`; include
    SNS MessageAttributes.

    On success return the publish response object.
    """
    # Extract TRE message (i.e. from tre-internal-topic)
    logger.info('event_record=%s', event_record)

    if KEY_BODY not in event_record:
        raise ValueError(f'Missing key {KEY_BODY} in event_record')
    body = json.loads(event_record[KEY_BODY])

    if KEY_MESSAGE not in body:
        raise ValueError(f'Missing key {KEY_BODY}.{KEY_MESSAGE} in event_record')
    message = json.loads(body[KEY_MESSAGE])
    logger.info('message=%s', message)

    if KEY_MESSAGE_ATTRIBUTES not in body:
        raise ValueError(f'Missing key {KEY_BODY}.{KEY_MESSAGE_ATTRIBUTES} in event_record')
    message_attributes = body[KEY_MESSAGE_ATTRIBUTES]
    logger.info('message_attributes=%s', message_attributes)
    
    # Create message attributes
    output_message_attributes_block = {
        key: {
            'DataType': value['Type'],
            'StringValue': value['Value']                
        } for key, value in message_attributes.items()
    }

    # Publish message to tre-out with message attributes
    publish_response = sns.publish(
        TopicArn=target_sns_arn,
        Message=json.dumps(message),
        MessageAttributes=output_message_attributes_block
    )

    logger.info('publish_response=%s', publish_response)
    
    # Check response code
    http_code = int(publish_response['ResponseMetadata']['HTTPStatusCode'])
    if http_code not in HTTP_OK_STATUS_CODES:
        error_message = (
            f'Event publish_response is {publish_response}'
        )

        logging.error(error_message)
        raise TREEventForwardError(error_message)
    
    # Execution was OK, return publish response
    return publish_response


def lambda_handler(event, context):
    """
    AWS invocation entry point.
    """
    logger.info('TRE_OUT_TOPIC_ARN=%s', TRE_OUT_TOPIC_ARN)
    logger.info('event=%s', event)

    if KEY_RECORDS not in event:
        raise ValueError(f'Missing key "{KEY_RECORDS}"')

    # Iterate over supplied records; may receive > 1
    forward_fail_list = []
    forward_ok_list = []

    for event_record in event[KEY_RECORDS]:
        try:
            execution_info = forward_tre_event_to_sns(
                event_record=event_record,
                target_sns_arn=TRE_OUT_TOPIC_ARN
            )

            forward_ok_list.append(execution_info)
        except Exception as e:
            logging.exception(e, stack_info=True)
            forward_fail_list.append(
                {
                    KEY_EVENT_RECORD: event_record,
                    KEY_ERROR: str(e)
                }
            )

    # Raise an error if there were any failed executions
    if len(forward_fail_list) > 0:
        logger.error('Error forwarding events: %s', forward_fail_list)
        error_list = [
            record[KEY_ERROR]
            for record in forward_fail_list
            if KEY_ERROR in record
        ]
        
        raise TREEventForwardError(
            f'Failed to process {len(forward_fail_list)}/'
            f'{len(event[KEY_RECORDS])} events; see log for detail, error '
            f'list is: {error_list}'
        )

    # Completed OK, return details of any step function execution(s)
    logger.info('Completed OK; forward_ok_list=%s', forward_ok_list)
    return json.dumps(forward_ok_list, default=str)
