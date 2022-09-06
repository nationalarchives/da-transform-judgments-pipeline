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
tre_out_topic_arn = os.environ['TRE_OUT_TOPIC_ARN']

def lambda_handler(event, context):
    logger.info(f'event:\n{event}')
    records = event['Records'][0]
    logger.info(f'Records:\n{records}')
    if records not in event:
        raise ValueError(f'Missing key "{records}"')

    # If >1 record, fail here so don't silently ignore unexpected records
    records_count = len(event[records])
    if records_count != 1:
        raise ValueError(f'Expected 1 record, got {records_count}')
    
    # Extract Meesage coming in from tre-internal-topic
    body = json.loads(records['body'])
    message = json.loads(body['Message'])
    logger.info(f'Message:\n{message}')
    message_attributes = body['MessageAttributes']
    logger.info(f'MessageAttributes:\n{message_attributes}')
    # Create message attributes
    message_attributes = {
        key:
            {
                'DataType': value['Type'],
                'StringValue': value['Value']                
            }
        for key, value in message_attributes.items()
    }

    # Publish message to tre-out with message attributes
    response = sns.publish(
        TopicArn = tre_out_topic_arn,
        Message = json.dumps(message),
        MessageAttributes = message_attributes
    )
    logger.info(f'MessageSent:\n{response}')
