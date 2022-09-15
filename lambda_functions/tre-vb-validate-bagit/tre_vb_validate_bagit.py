#!/usr/bin/env python3
"""
Lambda handler for validate-bagit Step Function step.
"""
import logging
import os
from urllib.parse import urlparse
from s3_lib import common_lib
from s3_lib import checksum_lib
from s3_lib import object_lib
from tre_event_lib import tre_event_api

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate this logger instance
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variable values
env_output_bucket = common_lib.get_env_var(
    'TRE_S3_BUCKET', must_exist=True, must_have_value=True)
env_producer = common_lib.get_env_var(
    'TRE_SYSTEM_NAME', must_exist=True, must_have_value=True)
env_process = common_lib.get_env_var(
    'TRE_PROCESS_NAME', must_exist=True, must_have_value=True)
env_environment = common_lib.get_env_var(
    'TRE_ENVIRONMENT', must_exist=True, must_have_value=True)

EVENT_NAME_INPUT = 'bagit-available'
EVENT_NAME_OUTPUT_OK = 'bagit-received'
EVENT_NAME_OUTPUT_ERROR = 'bagit-validation-error'

KEY_RESOURCE = 'resource'
KEY_RESOURCE_VALIDATION = 'resource-validation'
KEY_VALUE = 'value'
KEY_S3_BAGIT_NAME = 's3-bagit-name'


def handler(event, context):
    """
    Saves the BagIt and checksum files in the input's pre-signed URLs to S3
    and validates the BagIt's checksum matches the checksum file.

    Expected Input:
    * A `bagit-available` event

    Output:
    * A `bagit-received` event if validation is successful
    * A `bagit-validation-error` event if validation fails
    """
    logger.info('handler start')
    logger.info(f'type(event)="%s', type(event))
    logger.info(f'event:\n%s\n', event)
    tre_event_api.validate_event(event=event, schema_name=EVENT_NAME_INPUT)

    # Get required values from input event's parameter block
    input_params = event[tre_event_api.KEY_PARAMETERS][EVENT_NAME_INPUT]
    consignment_reference = input_params[tre_event_api.KEY_REFERENCE]
    s3_bagit_url = input_params[KEY_RESOURCE][KEY_VALUE]
    s3_sha_url = input_params[KEY_RESOURCE_VALIDATION][KEY_VALUE]
    consignment_type = event[tre_event_api.KEY_PRODUCER][tre_event_api.KEY_TYPE]
    # Get latest (last) UUID value from UUIDs list (list of dict)
    event_uuid = list(event[tre_event_api.KEY_UUIDS][-1].values())[0]
    logger.info(f'event_uuid=%s\n', event_uuid)

    try:
        # Determine output object path prefix
        output_object_prefix = (
            f'consignments/{consignment_type}/{consignment_reference}/'
            f'{event_uuid}')
        logger.info(f'output_object_prefix=%s\n', output_object_prefix)

        # Determine target s3 object names from the corresponding input URLs
        bagit_name = os.path.basename(urlparse(s3_bagit_url).path)
        logger.info(f'bagit_name=%s\n', bagit_name)
        s3_bagit_name = f'{output_object_prefix}/{bagit_name}'
        logger.info(f's3_bagit_name=%s\n', s3_bagit_name)
        sha_name = os.path.basename(urlparse(s3_sha_url).path)
        logger.info(f'sha_name=%s\n', sha_name)
        s3_sha_name = f'{output_object_prefix}/{sha_name}'
        logger.info(f's3_sha_name=%s\n', s3_sha_name)

        # Copy files
        logger.info(f'Copy "{s3_bagit_url}" to "{s3_bagit_name}" '
                    f'in "{env_output_bucket}"')
        object_lib.url_to_s3_object(
            s3_bagit_url, env_output_bucket, s3_bagit_name)
        logger.info(f'Copy "{s3_sha_url}" to "{s3_sha_name}" '
                    f'in "{env_output_bucket}"')
        object_lib.url_to_s3_object(s3_sha_url, env_output_bucket, s3_sha_name)

        # Load checksum(s) from the s3 manifest; there should be only 1 here
        s3_sha_manifest = checksum_lib.get_manifest_s3(
            env_output_bucket, s3_sha_name)

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

        output_parameter_block = {
            EVENT_NAME_OUTPUT_OK: {
                tre_event_api.KEY_REFERENCE: consignment_reference,
                tre_event_api.KEY_S3_BUCKET: env_output_bucket,
                KEY_S3_BAGIT_NAME: s3_bagit_name
            }
        }

        event_output_ok = tre_event_api.create_event(
            environment=env_environment,
            producer=env_producer,
            process=env_process,
            event_name=EVENT_NAME_OUTPUT_OK,
            prior_event=event,
            parameters=output_parameter_block)
        
        logger.info(f'event_output_ok:\n%s\n', event_output_ok)
        return event_output_ok
    except ValueError as e:
        logging.error(f'handler error: %s', str(e))
        output_parameter_block = {
            EVENT_NAME_OUTPUT_ERROR: {
                tre_event_api.KEY_REFERENCE: consignment_reference,
                tre_event_api.KEY_ERRORS: [str(e)]
            }
        }

        event_output_error = tre_event_api.create_event(
            environment=env_environment,
            producer=env_producer,
            process=env_process,
            event_name=EVENT_NAME_OUTPUT_ERROR,
            prior_event=event,
            parameters=output_parameter_block
        )

        logger.info(f'event_output_error:\n%s\n', event_output_error)
        return event_output_error
