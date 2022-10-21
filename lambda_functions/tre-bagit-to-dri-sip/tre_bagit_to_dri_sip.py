#!/usr/bin/env python3
import logging
from s3_lib import common_lib
from s3_lib import checksum_lib
from s3_lib import object_lib
from s3_lib import tar_lib
from tre_event_lib import tre_event_api
from tre_bagit_transforms import dri_config_dict
from tre_bagit import BagitData

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variable values
env_out_bucket = common_lib.get_env_var('S3_DRI_OUT_BUCKET', must_exist=True, must_have_value=True)
env_tre_presigned_url_expiry = common_lib.get_env_var('TRE_PRESIGNED_URL_EXPIRY', must_exist=True, must_have_value=True)
env_process = common_lib.get_env_var('TRE_PROCESS_NAME', must_exist=True, must_have_value=True)
env_producer = common_lib.get_env_var('TRE_SYSTEM_NAME', must_exist=True, must_have_value=True)
env_environment = common_lib.get_env_var('TRE_ENVIRONMENT', must_exist=True, must_have_value=True)

KEY_S3_OBJECT_ROOT = 's3-object-root'
KEY_S3_FOLDER_URL = 's3-folder-url'
KEY_S3_SHA256_URL = 's3-sha256-url'
KEY_FILE_TYPE = 'file-type'

EVENT_NAME_INPUT = 'bagit-validated'
EVENT_NAME_OUTPUT_OK = 'dri-preingest-sip-available'
EVENT_NAME_OUTPUT_ERROR = 'dri-preingest-sip-error'


def handler(event, context):
    """
    Given a bagit unzip sitting at event's "s3_object_root" then a dri-sip is provided in env var S3_DRI_OUT_BUCKET
    """
    logger.info(f'handler start: event="{event}"')

    tre_event_api.validate_event(event=event, schema_name=EVENT_NAME_INPUT)

    try:
        # Get input parameters from Lambda function's event object
        s3_data_bucket = event[tre_event_api.KEY_PARAMETERS][EVENT_NAME_INPUT][tre_event_api.KEY_S3_BUCKET]
        consignment_reference = event[tre_event_api.KEY_PARAMETERS][EVENT_NAME_INPUT][tre_event_api.KEY_REFERENCE]
        consignment_type = event[tre_event_api.KEY_PRODUCER][tre_event_api.KEY_TYPE]
        s3_object_root = event[tre_event_api.KEY_PARAMETERS][EVENT_NAME_INPUT][KEY_S3_OBJECT_ROOT]

        logger.info(
            f'consignment_reference="{consignment_reference}" '
            f'consignment_type="{consignment_type}" '
            f's3_data_bucket="{s3_data_bucket}" '
            f's3_object_root="{s3_object_root}" '
        )
        # set-up config_dicts x 3 & make bagit data
        s3c = s3_config_dict(s3_object_root)
        bc = bagit_config_dict()
        info_dict = object_lib.s3_object_to_dictionary(s3_data_bucket, s3c["PREFIX_TO_BAGIT"] + bc["BAG_INFO_TEXT"])
        manifest_dict = checksum_lib.get_manifest_s3(s3_data_bucket, s3c["PREFIX_TO_BAGIT"] + bc["BAGIT_MANIFEST"])
        csv_data = object_lib.s3_object_to_csv(s3_data_bucket, s3c["PREFIX_TO_BAGIT"] + bc["BAGIT_METADATA"])
        bagit_data = BagitData(bc, info_dict, manifest_dict, csv_data)
        dc = dri_config_dict(consignment_reference, bagit_data.consignment_series)
        # csv files
        closure_csv = bagit_data.to_closure(dc)
        object_lib.string_to_s3_object(closure_csv, s3_data_bucket, s3c["PREFIX_TO_SIP"] + dc["CLOSURE_IN_SIP"])
        metadata_csv = bagit_data.to_metadata(dc)
        object_lib.string_to_s3_object(metadata_csv, s3_data_bucket, s3c["PREFIX_TO_SIP"] + dc["METADATA_IN_SIP"])
        # checksums for csv files
        metadata_checksum = checksum_lib.get_s3_object_checksum(s3_data_bucket, s3c["PREFIX_TO_SIP"] + dc["METADATA_IN_SIP"])
        object_lib.string_to_s3_object(f'{metadata_checksum}  {dc["METADATA"]}\n',
                                       s3_data_bucket, s3c["PREFIX_TO_SIP"] + dc["METADATA_CHECKSUM_IN_SIP"])
        closure_checksum = checksum_lib.get_s3_object_checksum(s3_data_bucket, s3c["PREFIX_TO_SIP"] + dc["CLOSURE_IN_SIP"])
        object_lib.string_to_s3_object(f'{closure_checksum}  {dc["CLOSURE"]}\n',
                                       s3_data_bucket, s3c["PREFIX_TO_SIP"] + dc["CLOSURE_CHECKSUM_IN_SIP"])
        # write schemas
        with open('metadata-schema.txt') as file:
            object_lib.string_to_s3_object(file.read(), s3_data_bucket, s3c["PREFIX_TO_SIP"] + dc["METADATA_SCHEMA_IN_SIP"])
        with open('closure-schema.txt') as file:
            object_lib.string_to_s3_object(file.read(), s3_data_bucket, s3c["PREFIX_TO_SIP"] + dc["CLOSURE_SCHEMA_IN_SIP"])
        # zip it all up
        data_objects = object_lib.s3_ls(s3_data_bucket, s3c["PREFIX_TO_BAGIT"] + bc["PREFIX_FOR_DATA"])
        data_objects_to_zip = tar_lib.S3objectsToZip(data_objects, s3c["PREFIX_TO_BAGIT"] + bc["PREFIX_FOR_DATA"], dc["INTERNAL_PREFIX"])
        metadata_objects = object_lib.s3_ls(s3_data_bucket, s3c["PREFIX_TO_SIP"] + dc["INTERNAL_PREFIX"])
        metadata_objects_to_zip = tar_lib.S3objectsToZip(metadata_objects, s3c["PREFIX_TO_SIP"] + dc["INTERNAL_PREFIX"], dc["INTERNAL_PREFIX"])
        sip_zip_object = dc["BATCH"] + ".tar.gz"
        sip_zip_key= s3c["PREFIX_TO_SIP"] + sip_zip_object
        tar_lib.s3_objects_to_s3_tar_gz_file_with_prefix_substitution(
            s3_bucket_in=s3_data_bucket,
            s3_objects_with_prefix_subs=(metadata_objects_to_zip, data_objects_to_zip),
            tar_gz_object=sip_zip_key,
            s3_bucket_out=env_out_bucket
        )
        # make the checksum of the zip
        sip_zip_checksum = checksum_lib.get_s3_object_checksum(env_out_bucket, sip_zip_key)
        object_lib.string_to_s3_object(f'{sip_zip_checksum}  {sip_zip_object}\n', env_out_bucket, sip_zip_key + '.sha256')
        # make presigned urls and add to output message
        presigned_tar_gz_url = object_lib.get_s3_object_presigned_url(
            bucket=env_out_bucket,
            key=sip_zip_key,
            expiry=env_tre_presigned_url_expiry)
        presigned_checksum_url = object_lib.get_s3_object_presigned_url(
            bucket=env_out_bucket,
            key=sip_zip_key + '.sha256',
            expiry=env_tre_presigned_url_expiry)

        output_parameter_block = {
            EVENT_NAME_OUTPUT_OK: {
                tre_event_api.KEY_REFERENCE: consignment_reference,
                KEY_S3_FOLDER_URL: presigned_tar_gz_url,
                KEY_S3_SHA256_URL: presigned_checksum_url,
                KEY_FILE_TYPE:  "TAR"
            }
        }

        event_output_ok = tre_event_api.create_event(
            environment=env_environment,
            producer=env_producer,
            process=env_process,
            event_name=EVENT_NAME_OUTPUT_OK,
            prior_event=event,
            parameters=output_parameter_block
        )

        logger.info(f'event_output_ok:\n%s\n', event_output_ok)
        return event_output_ok

    except ValueError as e:
        logging.error('handler error: %s', str(e))
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


def bagit_config_dict():
    return dict(
        PREFIX_FOR_DATA='/data/',
        BAG_INFO_TEXT='/bag-info.txt',
        BAGIT_MANIFEST='/manifest-sha256.txt',
        BAGIT_METADATA='/file-metadata.csv'
    )


def s3_config_dict(s3_object_root):
    sip_directory = '/sip/'
    return dict(
        PREFIX_TO_BAGIT=s3_object_root,
        PREFIX_TO_SIP=s3_object_root + sip_directory
    )
