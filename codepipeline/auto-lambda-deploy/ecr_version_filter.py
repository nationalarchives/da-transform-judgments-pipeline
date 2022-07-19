#!/usr/bin/env python3
"""
Filter an ECR image version JSON payload and output either the newest version
(the default behavior of --max), the oldest version (--min), or a list of all
versions (--all) to stdout.

Version values of 'latest' are filtered out.

By default the JSON payload is read from stdin. Use the --file argument to
load JSON from a file, or the --json argument to supply a JSON string value.

The following optional arguments can be used:

--max : output the highest (latest) version present; this is the default
--min : output the lowest (oldest) version present
--all : output all the versions present; one per line in ascending order

The expected JSON input structure (e.g. from aws ecr list-images) is:

{"imageIds": [{"imageDigest": "...", "imageTag": "0.0.0"}]}

Examples:

aws ecr list-images \
    --repository-name="${ecr_repository_name}" \
    --filter tagStatus=TAGGED \
| ./ecr_version_filter.py

cat "${ecr_json_file}" | ./ecr_version_filter.py --all

./ecr_version_filter.py --max --file "${ecr_json_file}"
./ecr_version_filter.py --json "${ecr_json}"
"""
import sys
import json
from packaging import version
import argparse

parser = argparse.ArgumentParser(description=(
    'Filter an ECR image version JSON payload and output either the newest '
    'version (default), the oldest version, or a list of all versions.'))

meg1 = parser.add_mutually_exclusive_group()
meg1.add_argument('--file', help='Read JSON from given file (instead of stdin)')
meg1.add_argument('--json', help='Read JSON from given string (instead of stdin)')

meg2 = parser.add_mutually_exclusive_group()
meg2.add_argument('--all', action='store_true', help='List all versions')
meg2.add_argument('--min', action='store_true', help='Print lowest version')
meg2.add_argument('--max', action='store_true', help='Print highest version')

args = parser.parse_args()
ecr_image_json = None

if args.file is not None:
    with open(args.file) as f:
        ecr_image_json = json.load(f)
elif args.json is not None:
    ecr_image_json = json.loads(args.json)
else:
    ecr_image_json = json.load(sys.stdin)  # default to stdin
        
image_tags = [
    i['imageTag']
    for i in ecr_image_json['imageIds']
    if i['imageTag'].lower() != 'latest'
]

image_tags.sort(key=version.parse)

if len(image_tags) > 0:
    if args.all:
        print('\n'.join(image_tags))
    elif args.min:
        print(image_tags[0])
    else:
        print(image_tags[-1])  # default to --max
