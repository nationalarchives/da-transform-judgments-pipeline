import json
import boto3
import uuid
import os


client = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ['RAPB_ARN']
def lambda_handler(event, context):
    print(event)
    print(event['Records'])
    record = event['Records'][0]
    body = json.loads(record['body'])
    print(body)
    print(body['consignment-reference'])

    prefix = ""
    if 'consignment-reference' in body:
        prefix = body['consignment-reference']
    else:
        prefix = "X"

    retry = ""
    if 'number-of-retries' in body:
        retry = str(body['number-of-retries'])
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
		input = json.dumps(record)
		)
