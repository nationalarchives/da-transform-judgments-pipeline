from __future__ import print_function
from http import client
import json
import boto3
import uuid
import os


client = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ['SFN_ARN']
def lambda_handler(event, context):
    print(event)
    print(event['Records'])
    body = json.loads(event['Records'][0]['body'])
    print(body)
    print(body['consignment-reference'])

    prefix = ""
    if 'consignment-reference' in body:
        prefix = body['consignment-reference']
    else:
        prefix = "UNKNOWN-CONSIGNMENT-REF"
    

    unique_id = uuid.uuid4().hex

    response = client.start_execution(
		stateMachineArn = STATE_MACHINE_ARN,
		name = "tre-"+ prefix +"-" + unique_id,
		input = json.dumps(event['Records'][0])	
		)
