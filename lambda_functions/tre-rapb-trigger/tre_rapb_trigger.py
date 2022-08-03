import json
import boto3
import uuid
import os
import pprint


client = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ['RAPB_ARN']
def lambda_handler(event, context):
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(event)
    pp.pprint(event['Records'])
    record = event['Records'][0]
    body = json.loads(record['body'])
    pp.pprint(body)
    message = json.loads(body['Message'])
    pp.pprint(message)
    print(message['consignment-reference'])
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
		input = json.dumps(record)
		)
