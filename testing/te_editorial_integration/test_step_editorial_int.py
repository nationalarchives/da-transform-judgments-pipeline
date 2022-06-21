#!/usr/bin/env python3
import tre_editorial_integration
import sys
import json

if len(sys.argv) != 2:
    raise ValueError('usage: event')

event=sys.argv[1]
context=None

output = tre_editorial_integration.handler(json.loads(event), context)
print(f'te_editorial_integration output:\n{json.dumps(output, indent=4)}')
