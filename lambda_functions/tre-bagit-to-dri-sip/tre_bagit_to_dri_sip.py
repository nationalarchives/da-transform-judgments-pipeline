#!/usr/bin/env python3
import io
import logging
import csv
import urllib.parse
from s3_lib import common_lib
from s3_lib import checksum_lib
from s3_lib import object_lib
from s3_lib import tar_lib
from tre_event_lib import tre_event_api

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
KEY_NUMBER_OF_RETRIES = 'number-of-retries'
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
        bc = bagit_config_dict(consignment_reference)
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
                KEY_NUMBER_OF_RETRIES: 0,
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


def dri_config_dict(consignment_reference, consignment_series):
    metadata = 'metadata.csv'
    closure = 'closure.csv'
    consignment_reference_part = consignment_reference.split("-")
    tdr_year = consignment_reference_part[1]
    tdr_batch_number = consignment_reference_part[2]
    batch = consignment_series.replace(' ', '') + 'Y' + tdr_year[2:] + 'TB' + tdr_batch_number
    series = consignment_series.replace(' ', '_')
    internal_prefix = batch + '/' + series + '/'
    return dict(
        BATCH=batch,
        SERIES=series,
        INTERNAL_PREFIX=internal_prefix,
        IDENTIFIER_PREFIX='file:/' + internal_prefix,
        METADATA=metadata,
        CLOSURE=closure,
        METADATA_IN_SIP=internal_prefix + metadata,
        CLOSURE_IN_SIP=internal_prefix + closure,
        METADATA_SCHEMA_IN_SIP=internal_prefix + metadata + 's',
        CLOSURE_SCHEMA_IN_SIP=internal_prefix + closure + 's',
        METADATA_CHECKSUM_IN_SIP=internal_prefix + metadata + '.sha256',
        CLOSURE_CHECKSUM_IN_SIP=internal_prefix + closure + '.sha256'
    )


def bagit_config_dict(consignment_reference):
    return dict(
        CONSIGNMENT_REFERENCE=consignment_reference,
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


class BagitData:

    def __init__(self, config_dict, info_dict, manifest_dict, csv_data):
        self.bagit = config_dict
        self.info_dict = info_dict
        self.manifest_dict = manifest_dict
        self.csv_data = list(csv_data)
        self.consignment_series = self.info_dict.get('Consignment-Series')
        self.tdr_bagit_export_time = self.info_dict.get('Consignment-Export-Datetime')

    def to_metadata(self, dc):
        metadata_fieldnames = ['identifier', 'file_name', 'folder', 'date_last_modified', 'checksum',
                               'rights_copyright', 'legal_status', 'held_by', 'language', 'TDR_consignment_ref']
        metadata_output = io.StringIO()
        metadata_writer = csv.DictWriter(metadata_output, fieldnames=metadata_fieldnames, lineterminator="\n")
        metadata_writer.writeheader()
        for row in self.csv_data:
            metadata_writer.writerow({
                'identifier': self.dri_identifier(row, dc),
                'file_name': row.get('FileName'),
                'folder': self.dri_folder(row),
                'date_last_modified': self.dri_last_modified(row),
                'checksum': self.dri_checksum(row),
                'rights_copyright': row.get('RightsCopyright'),
                'legal_status': self.dri_legal_status(row),
                'held_by': self.dri_held_by(row),
                'language': row.get('Language'),
                'TDR_consignment_ref': self.bagit["CONSIGNMENT_REFERENCE"]})
        return metadata_output.getvalue()

    def to_closure(self, dc):
        closure_fieldnames = ['identifier', 'folder', 'closure_start_date', 'closure_period', 'foi_exemption_code',
                              'foi_exemption_asserted', 'title_public', 'title_alternate', 'closure_type']
        closure_output = io.StringIO()
        closure_writer = csv.DictWriter(closure_output, fieldnames=closure_fieldnames, lineterminator="\n")
        closure_writer.writeheader()
        for row in self.csv_data:
            closure_writer.writerow({
                'identifier': self.dri_identifier(row, dc),
                'folder': self.dri_folder(row),
                'closure_start_date': '',
                'closure_period': 0,
                'foi_exemption_code': row.get('FoiExemptionCode'),
                'foi_exemption_asserted': '',
                'title_public': 'TRUE',
                'title_alternate': '',
                'closure_type': 'open_on_transfer'
            })
        return closure_output.getvalue()

    # ==== specific transformations for individual field values ====
    @staticmethod
    def dri_folder(row):
        # remove capitalisation coming from tdr
        return row.get('FileType').lower()

    @staticmethod
    def dri_identifier(row, dc):
        # set dri batch/series/ prefix, escape the uri + append a `/` if folder
        dri_identifier = row.get('Filepath').replace('data/', dc["IDENTIFIER_PREFIX"], 1)
        final_slash_if_folder = "/" if(BagitData.dri_folder(row) == 'folder') else ""
        return urllib.parse.quote(dri_identifier).replace('%3A', ':') + final_slash_if_folder

    @staticmethod
    def dri_legal_status(row):
        # reword for Public Record
        return 'Public Record(s)' if(row.get('LegalStatus') == 'Public Record') else row.get('LegalStatus')

    @staticmethod
    def dri_held_by(row):
        # reword for TNA
        return 'The National Archives, Kew' if(row.get('HeldBy') == 'TNA') else row.get('HeldBy')

    def dri_checksum(self, row):
        # comes from the manifest and only exists for files
        bagit_manifest_for_row = list(filter(lambda d: d.get('file') == row.get('Filepath'), self.manifest_dict))
        return bagit_manifest_for_row[0].get('checksum') if(len(bagit_manifest_for_row) == 1) else ''

    def dri_last_modified(self, row):
        if self.dri_folder(row) == 'file':
            return row.get('LastModified')
        else:
            # use bagit export time for folders as they have no dlm from tdr
            return self.tdr_bagit_export_time.replace('Z', '', 1)
