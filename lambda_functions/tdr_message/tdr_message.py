from __future__ import print_function
from http import client
import json
import boto3
import uuid
import os


client = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ['SFN_ARN']
def lambda_handler(event, context):
    print(event['Records'])	
    for record in event['Records']:
        payload = json.loads(record["body"])
    
    unique_id = uuid.uuid4().hex
    print(payload)
    response = client.start_execution(
		stateMachineArn = STATE_MACHINE_ARN,
		name = "test_tna-" + unique_id,
		input = json.dumps(payload)	
		)
