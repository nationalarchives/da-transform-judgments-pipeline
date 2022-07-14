#!/usr/bin/env python3
import tdr_message
import sys
import json

if len(sys.argv) != 2:
    raise ValueError('usage: event')

records = sys.argv[1]
context = None

output = tdr_message.lambda_handler(json.loads(records), context)
print(f'tdr_message output:\n{json.dumps(output, indent=4)}')

