#!/usr/bin/env python3
import logging
from s3_lib import common_lib
from s3_lib import checksum_lib
from s3_lib import object_lib
from urllib.parse import urlparse
import os

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate this logger instance
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variable values
env_output_bucket = common_lib.get_env_var('S3_TEMPORARY_BUCKET', must_exist=True, must_have_value=True)

def handler(event, context):
    logger.info(f'handler start: event="{event}"')
    
    # Get input parameters from Lambda function's event object    
    consignment_reference = event['consignment-reference']
    s3_bagit_url = event['s3-bagit-url']
    s3_sha_url = event['s3-sha-url']
    consignment_type = event['consignment-type']
    number_of_retries = int(event['number-of-retries'])

    # Determine the resource name from the URL
    s3_bagit_name = os.path.basename(urlparse(s3_bagit_url).path)
    s3_sha_name = os.path.basename(urlparse(s3_sha_url).path)

    logger.info(
        f'consignment_reference="{consignment_reference}" '
        f's3_bagit_url="{s3_bagit_url}" s3_sha_url="{s3_sha_url}" '
        f'consignment_type="{consignment_type}" '
        f'number_of_retries="{number_of_retries}" '
        f's3_bagit_name="{s3_bagit_name}" s3_sha_name="{s3_sha_name}" '
        f'env_output_bucket="{env_output_bucket}"')

    # Copy files
    logger.info(f'Copy "{s3_bagit_url}" to "{s3_bagit_name}" in "{env_output_bucket}"')
    object_lib.url_to_s3_object(s3_bagit_url, env_output_bucket, s3_bagit_name)
    logger.info(f'Copy "{s3_sha_url}" to "{s3_sha_name}" in "{env_output_bucket}"')
    object_lib.url_to_s3_object(s3_sha_url, env_output_bucket, s3_sha_name)

    # Load checksum(s) from the source manifest; there should be only 1 here
    s3_sha_manifest = checksum_lib.get_manifest_url(s3_sha_url)
    
    # Only expect 1 checksum; verify this is so
    checksum_count = len(s3_sha_manifest)
    if checksum_count != 1:
        raise ValueError(
                f'Incorrect number of checksums; expected '
                f'1, found {checksum_count}')
    
    manifest_file = s3_sha_manifest[0][checksum_lib.ITEM_FILE]
    manifest_basename = s3_sha_manifest[0][checksum_lib.ITEM_BASENAME]
    expected_checksum = s3_sha_manifest[0][checksum_lib.ITEM_CHECKSUM]

    # Verify the file (basename) from the checksum file is in the s3 URL
    if manifest_basename != s3_bagit_name:
        raise ValueError(
                f'The name "{manifest_basename}" (derived from manifest file '
                f'entry "{manifest_file}") does not match the value '
                f'"{s3_bagit_name}" (derived from the input URL)')

    # Validate the main checksum
    checksum_lib.verify_s3_object_checksum(
            env_output_bucket,
            s3_bagit_name,
            expected_checksum)

    # Pass output data to next step
    logger.info('handler return')
    return {
        's3-bucket': env_output_bucket,
        's3-bagit-name': s3_bagit_name
    }
