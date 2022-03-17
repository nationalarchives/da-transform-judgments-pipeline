#!/usr/bin/env python3
import logging
from s3_lib import common_lib
from s3_lib import object_lib
from s3_lib import tar_lib
import json

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Error class
class TEEditorialIntegrationError(Exception):
    """
    Used to indicate a te_editorial_integration step specific error condition.
    """

# Get environment variable values
env_version_info = json.loads(common_lib.get_env_var('TE_VERSION_JSON', must_exist=True, must_have_value=True))
env_presigned_url_expiry = common_lib.get_env_var('TE_PRESIGNED_URL_EXPIRY', must_exist=True, must_have_value=True)
env_s3_bucket = common_lib.get_env_var('S3_BUCKET', must_exist=True, must_have_value=True)
env_s3_object_root = common_lib.get_env_var('S3_OBJECT_ROOT', must_exist=True, must_have_value=True)
env_s3_file_payload = common_lib.get_env_var('S3_FILE_PAYLOAD', must_exist=True, must_have_value=True)
env_s3_file_parser_xml = common_lib.get_env_var('S3_FILE_PARSER_XML', must_exist=True, must_have_value=True)
env_s3_file_parser_meta = common_lib.get_env_var('S3_FILE_PARSER_META', must_exist=True, must_have_value=True)
env_s3_file_bagit_info = common_lib.get_env_var('S3_FILE_BAGIT_INFO', must_exist=True, must_have_value=True)

KEY_CONSIGNMENT_REF='consignment-reference'
KEY_CONSIGNMENT_TYPE='consignment-type'
KEY_PRIOR_ATTEMPT_COUNT='number-of-retries'

def handler(event, context):
    """
    Given a set of parser output files at a predefined location:
    
    * Find the latest version of the requested judgement (i.e. the latest TDR
      data; this is determined from the s3 object path)
    * Ensure the current Editorial retry number has not been used
    * Use the current retry number in the s3 object key prefix (path) to:
        * Generate a JSON metadata file
        * Package the JSON metadata and parser files into a `tar.gz` archive
        * Generate a pre-shared URL for the `tar.gz` archive
        * Prepare a JSON message to send to Editorial (via subsequent SNS step)

    Expected input event format; number-of-retries is optional (default is 0):

    {
      "consignment-reference": "...",
      "consignment-type": "...",
      "number-of-retries": 0
    }

    SNS message format:
    {
      "consignment-reference": "TDR-...",
      "s3-folder-url": "...",
      "consignment-type": "judgment",
      "number-of-retries": 0
    }
    """
    logger.info(f'handler start: event="{event}"')
    validate_input(event)
    prior_attempt_count = int(event[KEY_PRIOR_ATTEMPT_COUNT]) if KEY_PRIOR_ATTEMPT_COUNT in event else 0                                                                                                                                                                                                                                                                                                                            
    consignment_reference = event[KEY_CONSIGNMENT_REF]
    consignment_type = event[KEY_CONSIGNMENT_TYPE]
    
    # Prior TDR stage number-of-retries is unknown when get an Editorial retry
    # message, so use the count in the TDR input path to find the latest one
    s3_object_latest_tdr_root = f'{env_s3_object_root}{consignment_type}/{consignment_reference}/'
    latest_tdr_retry = object_lib.get_max_s3_subfolder_number(env_s3_bucket, s3_object_latest_tdr_root)
    if latest_tdr_retry is None:
        raise TEEditorialIntegrationError('Unable to determine the latest retry count from the TDR stage')
    latest_tdr_retry = int(latest_tdr_retry)

    # Now we know where to read our input from, and write our output
    s3_input_path = f'{s3_object_latest_tdr_root}{latest_tdr_retry}'
    s3_output_path = f'{s3_input_path}/{prior_attempt_count}'
    logger.info(
        f'prior_attempt_count="{prior_attempt_count}" '
        f'latest_tdr_retry="{latest_tdr_retry}" '
        f'env_s3_bucket={env_s3_bucket} s3_input_path="{s3_input_path}" '
        f'consignment_reference={consignment_reference} '
        f'consignment_type={consignment_type} '
        f's3_output_path="{s3_output_path}"')
    
    input_objects = [
        f'{s3_input_path}/{env_s3_file_payload}',
        f'{s3_input_path}/{env_s3_file_parser_xml}',
        f'{s3_input_path}/{env_s3_file_parser_meta}'
    ]

    logger.info(f'input_objects={input_objects}')

    # Get latest used editorial retry number, from s3 (may be None):
    prior_ed_attempts_root = f'{s3_object_latest_tdr_root}{latest_tdr_retry}/'
    logger.info(f'prior_ed_attempts_root={prior_ed_attempts_root}')
    prior_ed_attempt_latest = object_lib.get_max_s3_subfolder_number(env_s3_bucket, prior_ed_attempts_root)
    expected_editorial_attempt = 0 if prior_ed_attempt_latest is None else 1 + int(prior_ed_attempt_latest)
    logger.info(f'prior_ed_attempt_latest={prior_ed_attempt_latest} expected_editorial_attempt={expected_editorial_attempt}')

    # Abort if not the expected attempt count
    if prior_attempt_count != expected_editorial_attempt:
        raise TEEditorialIntegrationError(
            f'Expected number-of-retries to be '
            f'"{expected_editorial_attempt}" but got "{prior_attempt_count}"')

    # Abort if objects already exist at output path for current "retry" number
    if object_lib.s3_object_exists(env_s3_bucket, s3_output_path):
        raise TEEditorialIntegrationError(
            f'Objects already exist in bucket "{env_s3_bucket}" with '
            f'prefix "{s3_output_path}" (retry {prior_attempt_count})')

    # Ensure the input objects exist in s3
    for input_object in input_objects:
        if not object_lib.s3_object_exists(env_s3_bucket, input_object):
            raise TEEditorialIntegrationError(
                f'Object "{input_object}" not found in bucket "{env_s3_bucket}"')

    output_tar_gz = f'{s3_output_path}/{consignment_reference}.tar.gz'
    logger.info(f'output_tar_gz={output_tar_gz}')

    # Get Bagit metadata as JSON key-value pairs
    bagit_info_s3_key = f'{s3_input_path}/{env_s3_file_bagit_info}'
    bagit_info_dict = object_lib.s3_object_to_dictionary(
        env_s3_bucket,
        bagit_info_s3_key)

    # Generate the editorial metadata content
    editorial_metadata = format_editorial_metadata(bagit_info_dict, env_version_info)

    # Create the metadata file
    editorial_metadata_s3_key = f'{s3_output_path}/te-metadata.json'
    object_lib.string_to_s3_object(
        json.dumps(editorial_metadata, indent=4),
        env_s3_bucket,
        editorial_metadata_s3_key)

    # Include the metadata file in the list of files for the tar.gz file
    input_objects.append(editorial_metadata_s3_key)

    # Write the list of s3 files to the output tar
    tar_items = tar_lib.s3_objects_to_s3_tar_gz_file(
        env_s3_bucket,
        input_objects,
        output_tar_gz,
        f'{consignment_reference}/')

    # Generate a presigned URL for the output tar.gz file
    presigned_tar_gz_url = object_lib.get_s3_object_presigned_url(
        env_s3_bucket,
        output_tar_gz,
        env_presigned_url_expiry)

    # Return summary information
    logger.info(f'handler return')
    return {
        'editorial-output': {
            'consignment-reference': consignment_reference,
            's3-folder-url': presigned_tar_gz_url,
            'consignment-type': consignment_type,
            'number-of-retries': prior_attempt_count
        },
        'tar-gz': {
            'bucket': env_s3_bucket,
            'key': output_tar_gz,
            'items': tar_items
        }
    }

def format_editorial_metadata(bagit_info, version_info):
    """
    Return a dictionary of editorial metadata content.
    """
    logger.info('create_editorial_metadata_file start')
    output = version_info.copy()
    output['uploader-email'] = bagit_info['Contact-Email']
    output['bagit-info'] = bagit_info
    logger.info(f'create_editorial_metadata_file return: output={output}')
    return output

def validate_input(event):
    """
    Raise an error if required input fields are missing.
    """
    missing_input_list = []
    if not KEY_CONSIGNMENT_REF in event:
        missing_input_list.append(KEY_CONSIGNMENT_REF)
    if not KEY_CONSIGNMENT_TYPE in event:
        missing_input_list.append(KEY_CONSIGNMENT_TYPE)
    if len(missing_input_list) > 0:
        raise TEEditorialIntegrationError(
            f'Missing mandatory inputs: {missing_input_list}')
