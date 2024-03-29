#!/usr/bin/env python3
import tre_bagit_checksum_validation
import tre_files_checksum_validation
import sys
import json

if len(sys.argv) != 2:
    raise ValueError('usage: event')

event=sys.argv[1]
context=None

output_bagit = tre_bagit_checksum_validation.handler(json.loads(event), context)
print(f'tre_bagit_checksum_validation output:\n{json.dumps(output_bagit, indent=4)}')

if str(output_bagit['error']).lower() != 'false':
    raise ValueError(output_bagit['error-message'])

output_files = tre_files_checksum_validation.handler(output_bagit, context)
print(f'tre_files_checksum_validation output:\n{json.dumps(output_files, indent=4)}')
