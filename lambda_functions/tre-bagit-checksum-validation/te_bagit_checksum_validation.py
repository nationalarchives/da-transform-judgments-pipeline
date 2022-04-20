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

KEY_NUM_RETRIES='number-of-retries'
KEY_BAGIT_URL='s3-bagit-url'
KEY_SHA_URL='s3-sha-url'
KEY_ERROR='error'
KEY_ERROR_MESSAGE='error-message'
KEY_S3_BUCKET='s3-bucket'
KEY_S3_BAGIT_NAME='s3-bagit-name'
KEY_OUTPUT_MESSAGE='output-message'

def handler(event, context):
    """
    Copy the content of the input URLs in `event` fields `s3-bagit-url` and
    `s3-sha-url` to s3 objects in the bucket name in environment variable
    `S3_TEMPORARY_BUCKET`; the following prefix is used for the s3 objects:
    
    * consignments/{consignment_type}/{consignment_reference}/{retry_count}

    The following checks are performed:
    
    * s3 files do not already exist
    * only 1 checksum is present in the manifest
    * the 1 manifest checksum matches the corresponding s3 file
    
    If a check fails the output dictionary's `error` field is set to `True`
    and field `error-message` reports the error message.

    The output message (described below) returns the operation outcome; this
    includes an `output-message` field that is a partial copy of the input
    `event` with field `number-of-retries` incremented by 1.

    Expected input event format:
    {
        "consignment-reference": "INPUT_FILE",
        "s3-bagit-url": "https://aws-bucket-name.s3.region.amazonaws.com/INPUT_FILE.tar.gz?X-Amz-Alg...",
        "s3-sha-url": "https://aws-bucket-name.s3.region.amazonaws.com/INPUT_FILE.tar.gz.sha256?X-Amz-Alg...",
        "consignment-type": "judgement",
        "number-of-retries": 0
    }

    Output message structure; `error-message` only present if `error` is True:

    {
        "error": True,
        "error-message": str(e),
        "output-message": {
            "consignment-reference": "INPUT_FILE",
            "s3-bagit-url": "",
            "s3-sha-url": "",
            "consignment-type": "judgement",
            "number-of-retries": 1
        },
        "s3-bucket": env_output_bucket,
        "s3-bagit-name": s3_bagit_name
    }

    Unexpected errors propogate as exceptions.
    """
    logger.info(f'handler start: event="{event}"')

    # Output data
    output = {
        KEY_ERROR: False,
        KEY_OUTPUT_MESSAGE: None,
        KEY_S3_BUCKET: env_output_bucket,
        KEY_S3_BAGIT_NAME: None
    }
    
    try:
        # Get input parameters from Lambda function's event object    
        consignment_reference = event['consignment-reference']
        s3_bagit_url = event[KEY_BAGIT_URL]
        s3_sha_url = event[KEY_SHA_URL]
        consignment_type = event['consignment-type']
        retry_count = int(event[KEY_NUM_RETRIES])

        # Create event copy with empty URLs
        output_event = event.copy()
        output_event[KEY_NUM_RETRIES] = retry_count
        output_event[KEY_BAGIT_URL] = ''
        output_event[KEY_SHA_URL] = ''
        logger.info(f'output_event={output_event}')
        output[KEY_OUTPUT_MESSAGE] = output_event

        # Determine output object path prefix
        output_object_prefix = (
            f'consignments/{consignment_type}/{consignment_reference}/'
            f'{retry_count}')

        # Determine target s3 object names from the corresponding input URLs
        bagit_name = os.path.basename(urlparse(s3_bagit_url).path)
        s3_bagit_name = f'{output_object_prefix}/{bagit_name}'
        output[KEY_S3_BAGIT_NAME] = s3_bagit_name
        sha_name = os.path.basename(urlparse(s3_sha_url).path)
        s3_sha_name = f'{output_object_prefix}/{sha_name}'

        logger.info(
            f'consignment_reference="{consignment_reference}" '
            f's3_bagit_url="{s3_bagit_url}" s3_sha_url="{s3_sha_url}" '
            f'consignment_type="{consignment_type}" '
            f'retry_count="{retry_count}" '
            f'bagit_name="{bagit_name}" sha_name="{sha_name}" '
            f's3_bagit_name="{s3_bagit_name}" s3_sha_name="{s3_sha_name}" '
            f'env_output_bucket="{env_output_bucket}"'
            f'output_object_prefix="{output_object_prefix}"')

        # Copy files
        logger.info(f'Copy "{s3_bagit_url}" to "{s3_bagit_name}" in "{env_output_bucket}"')
        object_lib.url_to_s3_object(s3_bagit_url, env_output_bucket, s3_bagit_name)
        logger.info(f'Copy "{s3_sha_url}" to "{s3_sha_name}" in "{env_output_bucket}"')
        object_lib.url_to_s3_object(s3_sha_url, env_output_bucket, s3_sha_name)

        # Load checksum(s) from the s3 manifest; there should be only 1 here
        s3_sha_manifest = checksum_lib.get_manifest_s3(env_output_bucket, s3_sha_name)
        
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
        if manifest_basename != bagit_name:
            raise ValueError(
                f'The name "{manifest_basename}" (derived from manifest file '
                f'entry "{manifest_file}") does not match the value '
                f'"{bagit_name}" (derived from the input URL)')

        # Validate the main checksum
        checksum_lib.verify_s3_object_checksum(
                env_output_bucket,
                s3_bagit_name,
                expected_checksum)
    except ValueError as e:
        logging.error(f'handler error: {str(e)}')
        output[KEY_ERROR] = True
        output[KEY_ERROR_MESSAGE] = str(e)
        output[KEY_OUTPUT_MESSAGE][KEY_NUM_RETRIES] = retry_count + 1

    # Set output data
    logger.info('handler return')
    return output
