#!/usr/bin/env python3
"""
Module to run tre_sqs_sf_trigger.handler; see corresponding run.sh file.
"""
import tre_sqs_sf_trigger
import sys
import json

if len(sys.argv) != 2:
    raise ValueError('usage: tre_message')

tre_message=json.loads(sys.argv[1])
context=None

event = {
    'Records': [
        {
            'eventSourceARN': 'arn:aws:sqs:example:00example000:some-sqs-in',
            'body': json.dumps(tre_message)
        }
    ]
}

result = tre_sqs_sf_trigger.handler(event=event, context=context)
print(f'result:\n{result}')
