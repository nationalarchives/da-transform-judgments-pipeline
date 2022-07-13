#!/usr/bin/env python3
import logging
from s3_lib import checksum_lib
from s3_lib import tar_lib
from s3_lib import object_lib
import os

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

KEY_ERROR='error'
KEY_ERROR_MESSAGE='error-message'
KEY_S3_BUCKET='s3-bucket'
KEY_S3_BAGIT_NAME='s3-bagit-name'
KEY_S3_OBJECT_ROOT='s3-object-root'
KEY_VALIDATED_FILES='validated-files'
KEY_OUTPUT_MESSAGE='output-message'
KEY_NUM_RETRIES='number-of-retries'

def handler(event, context):
    """
    Given input fields `s3-bucket` and `s3-bagit-name` in `event`:

    * Copy `output-message` from the input `event` into this handler's output
    * untar s3://`s3-bucket`/`s3-bagit-name` in place with existing path prefix
    * verify checksums of extracted tar's root files using file tagmanifest-sha256.txt
    * verify checksums of extracted tar's data directory files using file manifest-sha256.txt
    * verify the number of extracted files matches the numbers in the 2 manifest files

    Expected input event format:
    {
        "error": False,
        "output-message": ... ,
        "s3-bucket": env_output_bucket,
        "s3-bagit-name": s3_bagit_name
    }

    Output message structure; `error-message` only present if `error` is True:

    {
        "error": True,
        "error-message": str(e),
        "output-message":  ... ,
        "s3-bucket": "s3-bucket-name...",
        "s3-bagit-name": "consignments/.../.../1/tar.gz",
        "s3-object-root": "consignments/.../.../1/...",
        "validated-files": {
            "path": "consignments/.../.../1/...",
            "root": ["consignments/.../.../1/.../bag-info.txt", ... ],
            "data": ["consignments/.../.../1/.../data/doc.docx", ...]
        }
    }

    Unexpected errors propagate as exceptions.
    """
    logger.info(f'handler start: event="{event}"')

    # Output data
    output = {
        KEY_ERROR: False,
        KEY_S3_BUCKET: None,
        KEY_S3_OBJECT_ROOT: None,
        KEY_S3_BAGIT_NAME: None,
        KEY_VALIDATED_FILES: None,
        KEY_OUTPUT_MESSAGE: None
    }

    try:
        # Get input parameters
        s3_bucket = event['s3-bucket']
        output[KEY_S3_BUCKET] = s3_bucket
        s3_bagit_name = event['s3-bagit-name']
        logger.info(f's3_bucket="{s3_bucket}" s3_bagit_name="{s3_bagit_name}"')
        output[KEY_S3_BAGIT_NAME] = s3_bagit_name
        # Forward prior output-message
        output[KEY_OUTPUT_MESSAGE] = event[KEY_OUTPUT_MESSAGE].copy()
        retry_count = int(output[KEY_OUTPUT_MESSAGE][KEY_NUM_RETRIES])

        # Unpack tar in temporary bucket; use path prefix, if there is one
        output_prefix = os.path.split(s3_bagit_name)[0]
        output_prefix = output_prefix + '/' if len(output_prefix) > 0 else output_prefix
        extracted_object_list = tar_lib.untar_s3_object(
            s3_bucket, s3_bagit_name, output_prefix=output_prefix)
        logger.info(f'extracted_object_list={extracted_object_list}')

        # Verify extracted tar content checksums
        suffix = '.tar.gz'
        unpacked_folder_name = s3_bagit_name[:-len(suffix)] if s3_bagit_name.endswith(suffix) else s3_bagit_name
        output[KEY_S3_OBJECT_ROOT] = unpacked_folder_name
        checksum_ok_list = checksum_lib.verify_s3_manifest_checksums(s3_bucket, unpacked_folder_name)
        logger.info(f'checksum_ok_list={checksum_ok_list}')
        output[KEY_VALIDATED_FILES] = checksum_ok_list

        # Determine expected file counts (from manifest files)
        manifest_root_count = len(checksum_ok_list['root'])  # not main manifest itself
        manifest_data_count = len(checksum_ok_list['data'])
        # +1 file here as root manifest doesn't include itself (Catch-22...)
        manifests_total_count = 1 + manifest_root_count + manifest_data_count

        # Determine how many files were extracted from the archive
        extracted_total_count = len(extracted_object_list)

        # Determine how many of the extracted files are in the data sub-directory
        data_dir = f'{unpacked_folder_name}/data/'
        data_dir_files = [i for i in extracted_object_list if i.startswith(data_dir)]
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
        logger.info(f's3_check_list_count={s3_check_list_count} s3_check_dir={s3_check_dir}')
        if s3_check_list_count != extracted_total_count:
            raise ValueError(
                f'Incorrect data file count; {extracted_total_count} extracted'
                f'but {s3_check_list_count} found')            
    except ValueError as e:
        logging.error(f'handler error: {str(e)}')
        output[KEY_ERROR] = True
        output[KEY_ERROR_MESSAGE] = str(e)
        output[KEY_OUTPUT_MESSAGE][KEY_NUM_RETRIES] = retry_count + 1

    logger.info('handler return')
    return output
