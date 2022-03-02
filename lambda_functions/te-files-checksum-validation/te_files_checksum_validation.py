#!/usr/bin/env python3
import logging
from s3_lib import common_lib
from s3_lib import checksum_lib
from s3_lib import tar_lib
from urllib.parse import urlparse

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get environment variable values
env_output_bucket = common_lib.get_env_var('S3_TEMPORARY_BUCKET', must_exist=True, must_have_value=True)

def handler(event, context):
    logger.info(f'handler start: event="{event}"')
    
    # Get input parameters
    s3_bucket = event['s3-bucket']
    s3_bagit_name = event['s3-bagit-name']

    logger.info(f's3_bucket="{s3_bucket}" s3_bagit_name="{s3_bagit_name}"')

    # Unpack tar in temporary bucket
    tar_lib.untar_s3_object(env_output_bucket, s3_bagit_name)

    # Verify extracted tar content checksums
    suffix = '.tar.gz'
    unpacked_folder_name = s3_bagit_name[:-len(suffix)] if s3_bagit_name.endswith(suffix) else s3_bagit_name
    checksum_lib.verify_s3_manifest_checksums(env_output_bucket, unpacked_folder_name)

    # TODO: Verify file count

    logger.info('handler end')
