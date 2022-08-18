#!/usr/bin/env python3
import logging
from s3_lib import checksum_lib
from s3_lib import tar_lib
from s3_lib import object_lib
from s3_lib import common_lib
import os
from tre_lib.message import Message
from jsonschema import validate

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variable values
env_producer = common_lib.get_env_var(
    'TRE_SYSTEM_NAME', must_exist=True, must_have_value=True)
env_process = common_lib.get_env_var(
    'TRE_PROCESS_NAME', must_exist=True, must_have_value=True)
env_environment = common_lib.get_env_var(
    'TRE_ENVIRONMENT', must_exist=True, must_have_value=True)

OUTPUT_EVENT_NAME = 'bagit-validated'

KEY_NUM_RETRIES = 'number-of-retries'
KEY_REFERENCE = 'reference'
KEY_S3_BUCKET = 's3-bucket'
KEY_ERRORS = 'errors'
KEY_ERROR = 'error'
KEY_TYPE = 'type'
KEY_S3_BAGIT_NAME = 's3-bagit-name'
KEY_S3_OBJECT_ROOT = 's3-object-root'
KEY_VALIDATED_FILES = 'validated-files'


def validate_input(event: dict):
    """
    Validate the input event using JSON schema.
    """
    logger.info(f'validating event against message schema')
    schema_message = Message.get_schema()
    logger.info(f'schema={schema_message}')
    validate(instance=event, schema=schema_message)
    logger.info(f'event schema validation OK')

    schema_parameters_tdr = Message.get_schema(
        'schema_param_tre_validate_bagit.json')
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
        'schema_param_tre_validate_bagit_files.json')
    logger.info(f'schema={schema_param_tre}')
    parameters = output_message_dict[Message.KEY_PARAMETERS]
    logger.info(f'parameters={parameters}')
    validate(parameters, schema_param_tre)
    logger.info(f'output parameters schema validation OK')


def handler(event, context):
    """
    Given input fields `s3-bucket` and `s3-bagit-name` in `event`:

    * untar s3://`s3-bucket`/`s3-bagit-name` in place with existing path prefix
    * verify checksums of extracted tar's root files using file tagmanifest-sha256.txt
    * verify checksums of extracted tar's data directory files using file manifest-sha256.txt
    * verify the number of extracted files matches the numbers in the 2 manifest files

    Ref: https://github.com/nationalarchives/da-transform-dev-documentation/blob/master/architecture-decision-records/001-Enhanced-message-structure.md
    """
    logger.info(f'handler start"')
    logger.info(f'type(event)="{type(event)}')
    logger.info(f'event="{event}"')
    validate_input(event=event)
    logger.info(f'configuring initial output message')

    # Get required values from input event's parameters block
    consignment_type = event[Message.KEY_PRODUCER][KEY_TYPE]
    input_event_name = event[Message.KEY_PRODUCER][Message.KEY_EVENT_NAME]
    logger.info(f'input_event_name={input_event_name}')
    parameters = event[Message.KEY_PARAMETERS][input_event_name]
    s3_bucket = parameters[KEY_S3_BUCKET]
    consignment_reference = parameters[KEY_REFERENCE]
    s3_bagit_name = parameters[KEY_S3_BAGIT_NAME]
    retry_count = int(parameters[KEY_NUM_RETRIES])

    # Output data
    error_list = []

    # Setup initial output parameters block fields
    output_parameter_block = {
        OUTPUT_EVENT_NAME: {
            KEY_REFERENCE: consignment_reference,
            KEY_S3_BUCKET: s3_bucket,
            KEY_S3_BAGIT_NAME: s3_bagit_name,
            KEY_NUM_RETRIES: retry_count,
            KEY_ERRORS: error_list
        }
    }

    # Output message
    output_message = Message(
        producer=env_producer,
        process=env_process,
        event_name=OUTPUT_EVENT_NAME,
        environment=env_environment,
        type=consignment_type,
        prior_message=event,
        parameters=output_parameter_block)

    logger.info(f'output_message={output_message.to_json_str(indent=2)}')

    try:
        # Unpack tar in temporary bucket; use path prefix, if there is one
        output_prefix = os.path.split(s3_bagit_name)[0]
        output_prefix = output_prefix + \
            '/' if len(output_prefix) > 0 else output_prefix
        extracted_object_list = tar_lib.untar_s3_object(
            s3_bucket, s3_bagit_name, output_prefix=output_prefix)
        logger.info(f'extracted_object_list={extracted_object_list}')

        # Verify extracted tar content checksums
        suffix = '.tar.gz'
        unpacked_folder_name = s3_bagit_name[:-len(
            suffix)] if s3_bagit_name.endswith(suffix) else s3_bagit_name
        output_parameter_block[OUTPUT_EVENT_NAME][KEY_S3_OBJECT_ROOT] = unpacked_folder_name
        checksum_ok_list = checksum_lib.verify_s3_manifest_checksums(
            s3_bucket, unpacked_folder_name)
        logger.info(f'checksum_ok_list={checksum_ok_list}')
        output_parameter_block[OUTPUT_EVENT_NAME][KEY_VALIDATED_FILES] = checksum_ok_list

        # Determine expected file counts (from manifest files)
        # not main manifest itself
        manifest_root_count = len(checksum_ok_list['root'])
        manifest_data_count = len(checksum_ok_list['data'])
        # +1 file here as root manifest doesn't include itself (Catch-22...)
        manifests_total_count = 1 + manifest_root_count + manifest_data_count

        # Determine how many files were extracted from the archive
        extracted_total_count = len(extracted_object_list)

        # Determine how many of the extracted files are in the data sub-directory
        data_dir = f'{unpacked_folder_name}/data/'
        data_dir_files = [
            i for i in extracted_object_list if i.startswith(data_dir)]
        extracted_data_count = len(data_dir_files)

        logger.info(
            f'manifest_root_count={manifest_root_count} '
            f'manifest_data_count={manifest_data_count} '
            f'manifests_total_count={manifests_total_count} '
            f'extracted_total_count={extracted_total_count}'
            f'extracted_data_count={extracted_data_count}'
            f'data_dir_files={data_dir_files}')

        # Confirm untar output file count matches combined manifests' file count
        if extracted_total_count != manifests_total_count:
            raise ValueError(
                f'Incorrect total file count; {manifests_total_count} in '
                f'manifest, but {extracted_total_count} found')

        # Confirm correct number of files in extracted data sub-directory
        if manifest_data_count != extracted_data_count:
            raise ValueError(
                f'Incorrect data file count; {manifest_data_count} in manifest'
                f'but {extracted_data_count} found')

        # Verify there are no additional unexpected files in the s3 location
        s3_check_dir = f'{unpacked_folder_name}/'
        s3_check_list = object_lib.s3_ls(s3_bucket, s3_check_dir)
        s3_check_list_count = len(s3_check_list)
        logger.info(
            f's3_check_list_count={s3_check_list_count} s3_check_dir={s3_check_dir}')
        if s3_check_list_count != extracted_total_count:
            raise ValueError(
                f'Incorrect data file count; {extracted_total_count} extracted'
                f'but {s3_check_list_count} found')
    except ValueError as e:
        logging.error(f'handler error: {str(e)}')
        error_list.append({KEY_ERROR: str(e)})
        output_parameter_block[OUTPUT_EVENT_NAME][KEY_NUM_RETRIES] = retry_count + 1

    validate_output(output_message.to_dict())
    logger.info('handler completed OK')
    return output_message.to_dict()
