#!/usr/bin/env python3
import io
import logging
import csv
import urllib.parse
from s3_lib import common_lib
from s3_lib import checksum_lib
from s3_lib import object_lib
from s3_lib import tar_lib

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

KEY_NUM_RETRIES='number-of-retries'
KEY_ERROR='error'
KEY_ERROR_MESSAGE='error-message'
KEY_S3_BUCKET='s3-bucket'
KEY_OUTPUT_MESSAGE='output-message'


def handler(event, context):
    """
    Given a bagit unzip sitting in the s3-bucket in event and with location built from the event's
    type/consignemnt_ref/retry_number then a dri-sip is built in bucket provided in env variable S3_DRI_OUT_BUCKET at
    type/consignemnt_ref/retry_number/sip
    """
    logger.info(f'handler start: event="{event}"')

    # Output data
    output = {
        KEY_ERROR: False,
        KEY_OUTPUT_MESSAGE: None
    }

    try:
        # Get input parameters from Lambda function's event object
        s3_data_bucket = event['parameters']['TRE']['s3-bucket']
        consignment_reference = event['parameters']['TRE']['reference']
        consignment_type = event['producer']['type']
        retry_count = int(event['parameters']['TRE']['number-of-retries'])

        # Create event copy
        output_event = event.copy()
        output_event[KEY_NUM_RETRIES] = retry_count
        logger.info(f'output_event={output_event}')
        output[KEY_OUTPUT_MESSAGE] = output_event

        logger.info(
            f'consignment_reference="{consignment_reference}" '
            f'consignment_type="{consignment_type}" '
            f'retry_count="{retry_count}" '
            f's3_data_bucket="{s3_data_bucket}" ')
        # set-up config_dicts x 3 & make bagit data
        s3c = s3_config_dict(consignment_type, consignment_reference, retry_count)
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
        tar_lib.s3_objects_to_s3_tar_gz_file_with_prefix_substitution(
            s3_bucket_in=s3_data_bucket,
            s3_objects_with_prefix_subs=(metadata_objects_to_zip, data_objects_to_zip),
            tar_gz_object=s3c["PREFIX_TO_SIP"] + sip_zip_object,
            s3_bucket_out=env_out_bucket
        )
        # make the checksum of the zip
        sip_zip_checksum = checksum_lib.get_s3_object_checksum(env_out_bucket, s3c["PREFIX_TO_SIP"] + sip_zip_object)
        object_lib.string_to_s3_object(f'{sip_zip_checksum}  {sip_zip_object}\n', env_out_bucket, s3c["PREFIX_TO_SIP"] + sip_zip_object + ".sha256")

    except ValueError as e:
        logging.error(f'handler error: {str(e)}')
        output[KEY_ERROR] = True
        output[KEY_ERROR_MESSAGE] = str(e)
        output[KEY_OUTPUT_MESSAGE][KEY_NUM_RETRIES] = retry_count + 1

    # Set output data
    logger.info('handler return')
    return output


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
        PREFIX_FOR_DATA=consignment_reference + '/data/',
        BAG_INFO_TEXT=consignment_reference + '/bag-info.txt',
        BAGIT_MANIFEST=consignment_reference + '/manifest-sha256.txt',
        BAGIT_METADATA=consignment_reference + '/file-metadata.csv'
    )


def s3_config_dict(consignment_type, consignment_reference, retry_count):
    sip_directory = 'sip/'
    prefix_to_bagit = 'consignments/' + consignment_type + '/' + consignment_reference + '/' + str(retry_count) + '/'
    return dict(
        PREFIX_TO_BAGIT=prefix_to_bagit,
        PREFIX_TO_SIP=prefix_to_bagit + sip_directory
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
