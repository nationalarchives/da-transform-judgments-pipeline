#!/usr/bin/env python3
"""
Module to run tre_validate_bagit; see corresponding run.sh file.
"""
import tre_validate_bagit
import sys
import json

if len(sys.argv) != 2:
    raise ValueError('usage: event')

event=json.loads(sys.argv[1])
context=None

result = tre_validate_bagit.handler(event=event, context=context)
print(f'tre_validate_bagit output:\n{json.dumps(result, indent=2)}')
