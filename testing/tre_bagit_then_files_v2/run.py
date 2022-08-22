#!/usr/bin/env python3
"""
Module to run tre_validate_bagit then tre_validate_bagit_files.
See corresponding run.sh file.
"""
import tre_vb_validate_bagit
import tre_vb_validate_bagit_files
import sys
import json

if len(sys.argv) != 2:
    raise ValueError('usage: event')

event=json.loads(sys.argv[1])
context=None

result_1 = tre_vb_validate_bagit.handler(event=event, context=context)
print(f'tre_validate_bagit output:\n{json.dumps(result_1, indent=2)}')

result_2 = tre_vb_validate_bagit_files.handler(event=result_1, context=context)
print(f'tre_validate_bagit_files output:\n{json.dumps(result_2, indent=2)}')
