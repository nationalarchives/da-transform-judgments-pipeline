#!/usr/bin/env python3
import io
import json
import logging
import csv
from s3_lib import common_lib
from s3_lib import checksum_lib
from s3_lib import object_lib

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Get environment variable values
env_temp_bucket = common_lib.get_env_var('S3_TEMPORARY_BUCKET', must_exist=True, must_have_value=True)

KEY_NUM_RETRIES='number-of-retries'
KEY_ERROR='error'
KEY_ERROR_MESSAGE='error-message'
KEY_S3_BUCKET='s3-bucket'
KEY_OUTPUT_MESSAGE='output-message'

def handler(event, context):
    """
    Given a bagit unzip sitting in the temp-bucket determined by env var and with location built from the event's
    type/consignemnt_ref/retry_number then a dri-sip is built in the same temp-bucket at
    type/consignemnt_ref/retry_number/sip (and a zip + checksum of that zip are placed next to it)
    """
    logger.info(f'handler start: event="{event}"')

    # Output data
    output = {
        KEY_ERROR: False,
        KEY_OUTPUT_MESSAGE: None
    }

    try:
        # Get input parameters from Lambda function's event object
        consignment_reference = event['consignment-reference']
        consignment_type = event['consignment-type']
        retry_count = int(event[KEY_NUM_RETRIES])

        # Create event copy
        output_event = event.copy()
        output_event[KEY_NUM_RETRIES] = retry_count
        logger.info(f'output_event={output_event}')
        output[KEY_OUTPUT_MESSAGE] = output_event

        logger.info(
            f'consignment_reference="{consignment_reference}" '
            f'consignment_type="{consignment_type}" '
            f'retry_count="{retry_count}" '
            f'env_temp_bucket="{env_temp_bucket}" ')

        # Copy files into /sip/batch/series/content (TODO.. judgment input wont have content directory)
        prefix_to_bagit = 'consignments/' + consignment_type + '/' + consignment_reference + "/" + str(retry_count)
        prefix_for_data = prefix_to_bagit + "/" + consignment_reference + "/data/content/"
        bagit_info_text_key = prefix_to_bagit + "/" + consignment_reference + "/bag-info.txt"
        bagit_info_dict = object_lib.s3_object_to_dictionary(env_temp_bucket, bagit_info_text_key)
        bagit_manifest_key = prefix_to_bagit + "/" + consignment_reference + "/manifest-sha256.txt"
        bagit_manifest_dicts = checksum_lib.get_manifest_s3(env_temp_bucket, bagit_manifest_key)
        consignment_series = bagit_info_dict.get('Consignment-Series')
        consignment_reference_part = consignment_reference.split("-")
        tdr_year = consignment_reference_part[1]
        tdr_batch_number = consignment_reference_part[2]
        batch_without_number = consignment_series.replace(" ", "") + "Y" + tdr_year[2:] + "T"
        batch = batch_without_number + tdr_batch_number
        series = consignment_series.replace(" ", "_")
        # TODO: build file list from bagit_manifest_dicts rather than s3_ls?
        #  OR should we rely on actual file-metadata.csv (where is that list checked vs manifest?)
        #  OR even from event.json contains it? What do we consider definitive.  It could be very many files?
        #
        # TODO: is this copy files actually needed / wise?
        #  -- they could go straight into zip, with the new "path" - very close to that in s3_objects_to_s3_tar_gz_file
        #       (and we never need to copy over lots of files is attractive?)
        #  -- (and the other metadata files could work the same way i guess, but consider testing)
        f_list = object_lib.s3_ls(env_temp_bucket, prefix_for_data)
        for file in f_list:
            file_name = file.replace(prefix_for_data,"",1)
            to_key = prefix_to_bagit + "/sip/" + batch + "/" + series + "/content/" + file_name
            object_lib.copy_object(env_temp_bucket, file, env_temp_bucket, to_key)

        # prepare a csv for metadata and a csv for closure
        metadata_fieldnames = ['identifier', 'file_name', 'folder', 'date_last_modified', 'checksum', 'rights_copyright', 'legal_status', 'held_by', 'language', 'TDR_consignment_ref']
        metadata_output = io.StringIO()
        metadata_writer = csv.DictWriter(metadata_output, fieldnames=metadata_fieldnames)
        metadata_writer.writeheader()
        closure_fieldnames = ['identifier', 'folder', 'closure_start_date', 'closure_period', 'foi_exemption_code', 'foi_exemption_asserted', 'title_public', 'title_alternate', 'closure_type']
        closure_output = io.StringIO()
        closure_writer = csv.DictWriter(closure_output, fieldnames=closure_fieldnames)
        closure_writer.writeheader()
        dri_identifier_prefix = "file:/" + batch + "/" + series + "/"
        # iterate over bagit metadata csv, making new csv for dri metadata and csv for dri closure
        bagit_metadata = prefix_to_bagit + "/" + consignment_reference + "/file-metadata.csv"
        csv_data = object_lib.s3_object_to_csv(env_temp_bucket, bagit_metadata)
        for row in csv_data:
            dri_identifier = row.get('Filepath').replace("data/", dri_identifier_prefix, 1)
            dri_legal_status = 'Public Record(s)' if(row.get('LegalStatus') == 'Public Record') else row.get('LegalStatus')
            dri_held_by = 'The National Archives, Kew' if(row.get('HeldBy') == 'TNA') else row.get('HeldBy')
            dri_folder = row.get('FileType')
            bagit_manifest_for_row = list(filter(lambda d: d.get('file') == row.get('Filepath'), bagit_manifest_dicts))
            dri_checksum = bagit_manifest_for_row[0].get('checksum') if(len(bagit_manifest_for_row) == 1) else ''
            metadata_writer.writerow({
                'identifier': dri_identifier,
                'file_name': row.get('FileName'),
                'folder': dri_folder,
                'date_last_modified': row.get('LastModified'),
                'checksum': dri_checksum,
                'rights_copyright': row.get('RightsCopyright'),
                'legal_status': dri_legal_status,
                'held_by': dri_held_by,
                'language': row.get('Language'),
                'TDR_consignment_ref': consignment_reference})
            closure_writer.writerow({
                'identifier': dri_identifier,
                'folder': dri_folder,
                'closure_start_date': '',
                'closure_period': 0,
                'foi_exemption_code': row.get('FoiExemptionCode'),
                'foi_exemption_asserted': '',
                'title_public': 'TRUE',
                'title_alternate': '',
                'closure_type': 'open_on_transfer'
            })
        # write csv files
        prefix_to_sip = prefix_to_bagit + "/sip/"
        dri_metadata_in_sip = batch + "/" + series + "/metadata_" + batch + ".csv"
        dri_closure_in_sip = batch + "/" + series + "/closure.csv"
        key_for_dri_metadata = prefix_to_sip + dri_metadata_in_sip
        key_for_dri_closure = prefix_to_sip + dri_closure_in_sip
        object_lib.string_to_s3_object(closure_output.getvalue(), env_temp_bucket, key_for_dri_closure)
        object_lib.string_to_s3_object(metadata_output.getvalue(), env_temp_bucket, key_for_dri_metadata)
        # write checksums for csv files
        metadata_checksum = checksum_lib.get_s3_object_checksum(env_temp_bucket, key_for_dri_metadata)
        object_lib.string_to_s3_object(f'{metadata_checksum} {dri_metadata_in_sip}', env_temp_bucket, key_for_dri_metadata + ".sha256")
        closure_checksum = checksum_lib.get_s3_object_checksum(env_temp_bucket, key_for_dri_closure)
        object_lib.string_to_s3_object(f'{closure_checksum} {dri_closure_in_sip}', env_temp_bucket, key_for_dri_closure + ".sha256")
        # write schemas
        # TODO: these text files are just alongside the test-bagit-to-dri-sip.py, need to figure out paths / including in build etc.
        key_for_dri_metadata_schema = prefix_to_sip + batch + "/" + series + "/metadata_" + batch_without_number + "000.csvs"
        key_for_dri_closure_schema = prefix_to_sip + dri_closure_in_sip + "s"
        with open('metadata-schema.txt') as file:
            object_lib.string_to_s3_object(file.read(), env_temp_bucket, key_for_dri_metadata_schema)
        with open('closure-schema.txt') as file:
            object_lib.string_to_s3_object(file.read(), env_temp_bucket, key_for_dri_closure_schema)
        # zip it all up and write a checksum the zip..
        # TODO: make that zip, but first think about comments on whether the copy is need in the TODO above


    except ValueError as e:
        logging.error(f'handler error: {str(e)}')
        output[KEY_ERROR] = True
        output[KEY_ERROR_MESSAGE] = str(e)
        output[KEY_OUTPUT_MESSAGE][KEY_NUM_RETRIES] = retry_count + 1

    # Set output data
    logger.info('handler return')
    return output


