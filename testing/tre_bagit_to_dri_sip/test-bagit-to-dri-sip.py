#!/usr/bin/env python3
import tre_bagit_to_dri_sip
import sys
import json

if len(sys.argv) != 2:
    raise ValueError('usage: event')

event = sys.argv[1]
context = None

output = tre_bagit_to_dri_sip.handler(json.loads(event), context)
print(f'bagit_to_dri_sip output:\n{json.dumps(output, indent=4)}')

