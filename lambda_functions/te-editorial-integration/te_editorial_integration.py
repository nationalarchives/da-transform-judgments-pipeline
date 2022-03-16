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

KEY_CONSIGNMENT_REF='consignment-reference'
KEY_CONSIGNMENT_TYPE='consignment-type'
KEY_S3_BUCKET='s3-bucket'
KEY_S3_OBJECT_ROOT='s3-object-root'
KEY_S3_FILES='parsed-files'
KEY_S3_FILE_PAYLOAD='judgment'
KEY_S3_FILE_PARSER_XML='xml'
KEY_S3_FILE_PARSER_META_JSON='meta'
KEY_S3_FILE_BAG_INFO='bagit-info'

def handler(event, context):
    """
    Given a set of parser output files in `event` this handler function will:
    
    * generate a JSON metadata file
    * package the JSON metadata and parser files into a `tar.gz` archive
    * generate a pre-shared URL for the `tar.gz` archive
    * prepare a JSON message for a subsequent step function SNS action

    Expected input event format:
    {
      "s3-bucket": "...",
      "s3-object-root": "...",
      "consignment-reference": "...",
      "consignment-type": "...",
      "parsed-files": {
         "judgement": "---/---.docx",
         "xml": "---/---.xml",
         "meta": "---/---.json",
         "bagit-info": "---/---.txt"
      }
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
    s3_bucket = event[KEY_S3_BUCKET]
    s3_object_root = event[KEY_S3_OBJECT_ROOT]
    consignment_reference = event[KEY_CONSIGNMENT_REF]
    consignment_type = event[KEY_CONSIGNMENT_TYPE]
    s3_output_path = f'{s3_object_root}/{prior_attempt_count}'
    logger.info(
        f'prior_attempt_count="{prior_attempt_count}" '
        f's3_bucket={s3_bucket} s3_object_root="{s3_object_root}" '
        f'consignment_reference={consignment_reference} '
        f'consignment_type={consignment_type} '
        f's3_output_path="{s3_output_path}"')
    
    input_objects = [
        event[KEY_S3_FILES][KEY_S3_FILE_PAYLOAD],
        event[KEY_S3_FILES][KEY_S3_FILE_PARSER_XML],
        event[KEY_S3_FILES][KEY_S3_FILE_PARSER_META_JSON],
        event[KEY_S3_FILES][KEY_S3_FILE_BAG_INFO]
    ]

    logger.info(f'input_objects={input_objects}')

    # Abort if objects already exist at output path for current "retry" number
    if object_lib.s3_object_exists(s3_bucket, s3_output_path):
        raise TEEditorialIntegrationError(
            f'Objects already exist in bucket "{s3_bucket}" with '
            f'prefix "{s3_output_path}" (retry {prior_attempt_count})')

    # Ensure the input objects exist in s3
    for input_object in input_objects:
        if not object_lib.s3_object_exists(s3_bucket, input_object):
            raise TEEditorialIntegrationError(
                f'Object "{input_object}" not found in bucket "{s3_bucket}"')

    output_tar_gz = f'{s3_output_path}/{consignment_reference}.tar.gz'
    logger.info(f'output_tar_gz={output_tar_gz}')

    # Get bagit metadata as JSON key-value pairs
    bagit_info_s3_key = event[KEY_S3_FILES][KEY_S3_FILE_BAG_INFO]
    bagit_info_dict = object_lib.s3_object_to_dictionary(
        s3_bucket,
        bagit_info_s3_key)

    # Generate the editorial metadata content
    editorial_metadata = format_editorial_metadata(bagit_info_dict, env_version_info)

    # Create the metadata file
    editorial_metadata_s3_key = f'{s3_output_path}/te-metadata.json'
    object_lib.string_to_s3_object(
        json.dumps(editorial_metadata, indent=4),
        s3_bucket,
        editorial_metadata_s3_key)

    # Include the metadata file in the list of files for the tar.gz file
    input_objects.append(editorial_metadata_s3_key)

    # Write the list of s3 files to the output tar
    tar_items = tar_lib.s3_objects_to_s3_tar_gz_file(
        s3_bucket,
        input_objects,
        output_tar_gz,
        f'{consignment_reference}/')

    # Generate a presigned URL for the output tar.gz file
    presigned_tar_gz_url = object_lib.get_s3_object_presigned_url(
        s3_bucket,
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
            'bucket': s3_bucket,
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
