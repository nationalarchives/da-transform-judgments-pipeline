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
env_parser_bucket_in = common_lib.get_env_var('S3_PARSER_INPUT_BUCKET', must_exist=True, must_have_value=True)
env_parser_bucket_out = common_lib.get_env_var('S3_PARSER_OUTPUT_BUCKET', must_exist=True, must_have_value=True)
env_version_info = json.loads(common_lib.get_env_var('TE_VERSION_JSON', must_exist=True, must_have_value=True))
env_presigned_url_expiry = common_lib.get_env_var('TE_PRESIGNED_URL_EXPIRY', must_exist=True, must_have_value=True)

KEY_S3_BAGIT_PATH='bagit-path'
KEY_S3_PARSER_PATH='parser-path'
KEY_CONSIGNMENT_REF='consignment-reference'
KEY_CONSIGNMENT_TYPE='consignment-type'
KEY_S3_OBJECT_ROOT='s3-object-root'

def handler(event, context):
    """
    Given a set of parser output files at the location specified by `event`
    field `s3-parser-location` in the s3 bucket specified by environment
    variable `S3_INPUT_BUCKET`, this handler function will:
    
    * generate a JSON metadata file
    * package the JSON metadata and parser files into a `tar.gz` archive
    * generate a pre-shared URL for the `tar.gz` archive
    * prepare a JSON message for a subsequent step function SNS action

    Expected input event format:
    {
      "bagit-path": "...",
      "parser-path": "...",
      "consignment-reference": "TDR-..."
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
    prior_attempt_count = 0
    consignment_reference = event[KEY_CONSIGNMENT_REF]
    consignment_type = event[KEY_CONSIGNMENT_TYPE]
    s3_bagit_path = event[KEY_S3_BAGIT_PATH]
    s3_root_parser_path = event[KEY_S3_PARSER_PATH]
    s3_output_path = f'{s3_root_parser_path}/{prior_attempt_count}'
    logger.info(
        f'prior_attempt_count="{prior_attempt_count}" '
        f'consignment_reference={consignment_reference} '
        f'consignment_type={consignment_type} '
        f's3_root_parser_path="{s3_root_parser_path}" '
        f's3_output_path="{s3_output_path}"')
    
    # Abort if there are no input files
    input_objects = object_lib.s3_ls(env_parser_bucket_out, s3_root_parser_path)
    logger.info(f'input_objects={input_objects}')
    if len(input_objects) == 0:
        raise TEEditorialIntegrationError(
            f'No input objects found in bucket  "{env_parser_bucket_out}" with '
            f'prefix "{s3_root_parser_path}" (retry {prior_attempt_count})')

    # Abort if objects already exist at output path for current "retry" number
    if object_lib.s3_object_exists(env_parser_bucket_out, s3_output_path):
        raise TEEditorialIntegrationError(
            f'Objects already exist in bucket "{env_parser_bucket_out}" with '
            f'prefix "{s3_output_path}" (retry {prior_attempt_count})')

    output_tar_gz = f'{s3_output_path}/{consignment_reference}.tar.gz'
    logger.info(f'output_tar_gz={output_tar_gz}')

    # Get bagit metadata as JSON key-value pairs
    bagit_info_s3_key = f'{s3_bagit_path}/bag-info.txt'
    bagit_info_dict = object_lib.s3_object_to_dictionary(
        env_parser_bucket_in,
        bagit_info_s3_key)

    # Generate the editorial metadata content
    editorial_metadata = format_editorial_metadata(bagit_info_dict, env_version_info)

    # Create the metadata file
    editorial_metadata_s3_key = f'{s3_output_path}/te-metadata.json'
    object_lib.string_to_s3_object(
        json.dumps(editorial_metadata, indent=4),
        env_parser_bucket_out,
        editorial_metadata_s3_key)

    # Include the metadata file in the list of files for the tar.gz file
    input_objects.append(editorial_metadata_s3_key)

    # Write the list of s3 files to the output tar
    tar_items = tar_lib.s3_objects_to_s3_tar_gz_file(
        env_parser_bucket_out,
        input_objects,
        output_tar_gz,
        f'{consignment_reference}/')

    # Generate a presigned URL for the output tar.gz file
    presigned_tar_gz_url = object_lib.get_s3_object_presigned_url(
        env_parser_bucket_out,
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
            'bucket': env_parser_bucket_out,
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
    output['uploader-email'] = bagit_info['Contact-Email']  # TODO: remove, replaced by 'bagit-info'?
    output['bagit-info'] = bagit_info
    logger.info(f'create_editorial_metadata_file return: output={output}')
    return output
