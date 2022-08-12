import json
import boto3
import uuid
import os


client = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ['RAPB_ARN']
def lambda_handler(event, context):
    print(f" Event: {(json.dumps(event, indent=2))}")
    record = event['Records'][0]
    print(f"Records: {json.dumps(record, indent=2)}")
    body = json.loads(record['body'])
    print(f"Body: {(json.dumps(body, indent=2))}")
    message = json.loads(body['Message'])
    print(f"Message: {(json.dumps(message, indent=2))}")
    print(f" Consignment-Reference: {(message['consignment-reference'])}")
    prefix = ""
    if 'consignment-reference' in message:
        prefix = message['consignment-reference']
    else:
        prefix = "X"

    retry = ""
    if 'number-of-retries' in message:
        retry = str(message['number-of-retries'])
    else:
        retry = "X"

    event_source = ""
    if 'eventSourceARN' in record:
        arn = record['eventSourceARN']
        event_source = arn.split(':')[5]
    else:
        event_source = "X"

    unique_id = uuid.uuid4().hex

    name = "tre-" + prefix + "-" + retry + "-" + event_source + "-" + unique_id
    
    response = client.start_execution(
        stateMachineArn = STATE_MACHINE_ARN,
        name = name,
        input = json.dumps(message)
    )
