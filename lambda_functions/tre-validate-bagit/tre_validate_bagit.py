#!/usr/bin/env python3
import logging
from s3_lib import common_lib
from s3_lib import checksum_lib
from s3_lib import object_lib
from urllib.parse import urlparse
import os
from tre_lib.message import Message
from jsonschema import validate


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

KEY_ERRORS = 'errors'
KEY_ERROR = 'error'
KEY_S3_BUCKET = 's3-bucket'
KEY_NUM_RETRIES = 'number-of-retries'
KEY_REFERENCE = 'reference'
KEY_RESOURCE = 'resource'
KEY_RESOURCE_VALIDATION = 'resource-validation'
KEY_VALUE = 'value'
KEY_PRODUCER = 'producer'
KEY_TYPE = 'type'
KEY_S3_BAGIT_NAME = 's3-bagit-name'
KEY_TDR = 'TDR'


def validate_input(event: dict):
    """
    Validate the input event using JSON schema.
    """
    logger.info(f'validating event against message schema')
    schema_message = Message.get_schema()
    logger.info(f'schema={schema_message}')
    validate(instance=event, schema=schema_message)
    logger.info(f'event schema validation OK')

    schema_parameters_tdr = Message.get_schema('schema_param_tdr_to_tre.json')
    logger.info(f'validating event parameters against expected schema')
    logger.info(f'schema={schema_parameters_tdr}')
    validate(
        instance=event[Message.KEY_PARAMETERS],
        schema=schema_parameters_tdr)
    logger.info(f'event parameter schema validation OK')


def validate_output(output_message_dict: dict):
    """
    Validate the output message using JSON schema.
    """
    logger.info(f'validating output_message against schema')
    logger.info(f'output_message_dict={output_message_dict}')
    validate(output_message_dict, Message.get_schema())
    logger.info(f'output_message schema validation OK')
    logger.info(f'validating output parameters against schema')
    schema_param_tre = Message.get_schema(
        'schema_param_tre_validate_bagit.json')
    logger.info(f'schema={schema_param_tre}')
    parameters = output_message_dict[Message.KEY_PARAMETERS]
    logger.info(f'parameters={parameters}')
    validate(parameters, schema_param_tre)
    logger.info(f'output parameters schema validation OK')


def handler(event, context):
    """
    Copy the content of the input URLs in `event` fields `s3-bagit-url` and
    `s3-sha-url` to s3 objects in the bucket name in environment variable
    `TRE_S3_BUCKET`; the following prefix is used for the s3 objects:

    * consignments/{consignment_type}/{consignment_reference}/{retry_count}

    The following checks are performed:

    * S3 files do not already exist
    * Only 1 checksum is present in the manifest
    * The 1 manifest checksum matches the corresponding s3 file

    Ref: https://github.com/nationalarchives/da-transform-dev-documentation/blob/master/architecture-decision-records/001-Enhanced-message-structure.md
    """
    logger.info(f'handler start')
    logger.info(f'type(event)="{type(event)}')
    logger.info(f'event="{event}"')
    validate_input(event=event)
    logger.info(f'configuring initial output message')

    # Get required values from input event's parameters block
    tdr_params = event[Message.KEY_PARAMETERS][KEY_TDR]
    consignment_reference = tdr_params[KEY_REFERENCE]
    s3_bagit_url = tdr_params[KEY_RESOURCE][KEY_VALUE]
    s3_sha_url = tdr_params[KEY_RESOURCE_VALIDATION][KEY_VALUE]
    consignment_type = event[KEY_PRODUCER][KEY_TYPE]
    retry_count = int(tdr_params[KEY_NUM_RETRIES])
    error_list = []

    # Setup initial output parameters block fields
    output_parameter_block = {
        env_producer: {
            KEY_REFERENCE: consignment_reference,
            KEY_S3_BUCKET: env_output_bucket,
            KEY_NUM_RETRIES: retry_count,
            KEY_ERRORS: error_list
        }
    }

    # Output message
    output_message = Message(
        producer=env_producer,
        process=env_process,
        environment=env_environment,
        type=consignment_type,
        prior_message=event,
        parameters=output_parameter_block)

    logger.info(f'output_message={output_message.to_json_str(indent=2)}')

    try:
        # Determine output object path prefix
        output_object_prefix = (
            f'consignments/{consignment_type}/{consignment_reference}/'
            f'{retry_count}')

        # Determine target s3 object names from the corresponding input URLs
        bagit_name = os.path.basename(urlparse(s3_bagit_url).path)
        s3_bagit_name = f'{output_object_prefix}/{bagit_name}'
        output_parameter_block[env_producer][KEY_S3_BAGIT_NAME] = s3_bagit_name
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
    except ValueError as e:
        logging.error(f'handler error: {str(e)}')
        error_list.append({KEY_ERROR: str(e)})
        output_parameter_block[env_producer][KEY_NUM_RETRIES] = retry_count + 1

    validate_output(output_message.to_dict())
    logger.info('handler completed OK')
    return output_message.to_dict()
