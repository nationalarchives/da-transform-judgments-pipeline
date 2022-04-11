#!/usr/bin/env python3
import logging
import boto3  # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/index.html
import tarfile  # https://docs.python.org/3/library/tarfile.html
import io
import os
from s3_lib import common_lib

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

KEY_BUCKET_IN = 'input-bucket'
KEY_OBJECT_IN = 'input-object'
KEY_BUCKET_OUT = 'output-bucket'
KEY_FILES = 'extracted-tar-files'

def untar_s3_object(
        input_bucket_name,
        object_name,
        output_prefix='',
        output_bucket_name=None):
    """
    Perform an untar operation on the specified s3 `object_name` in
    `input_bucket_name`. Output is to `input_bucket_name` unless
    `output_bucket_name` is provided. Output object names from the tar can be
    prefixed with `output_prefix`.
    """
    logger.info(
            f'untar_s3_object start: input_bucket_name={input_bucket_name} '
            f'object_name={object_name} '
            f'output_prefix={output_prefix} '
            f'output_bucket_name={output_bucket_name}')

    output_bucket_name = input_bucket_name if output_bucket_name is None else output_bucket_name
    s3_client = boto3.client('s3')
    s3_input_object = s3_client.get_object(Bucket=input_bucket_name, Key=object_name)
    tar_stream = io.BytesIO(s3_input_object['Body'].read())
    extracted_object_names = []

    with tarfile.open(fileobj=tar_stream) as tar_content:
        for item in tar_content:
            logger.info(f'item.isdir()={item.isdir()} item.isFile()={item.isfile()} item.name={item.name} item={item}')
            if item.isfile():
                # No .removeprefix method in Python 3.8; check with if instead
                output_object_name = item.name[2:] if item.name.startswith('./') else item.name
                output_object_name = output_prefix + output_object_name
                logger.info(f'output_object_name={output_object_name}')
                item_stream = tar_content.extractfile(item).read()
                s3_client.upload_fileobj(
                    io.BytesIO(item_stream),
                    Bucket=output_bucket_name,
                    Key=output_object_name)
                # Add extracted object's name to output summary
                extracted_object_names.append(output_object_name)

    logger.info('untar_s3_object return')
    return extracted_object_names

def s3_objects_to_s3_tar_gz_file(
        s3_bucket_in,
        s3_object_names,
        tar_gz_object,
        tar_internal_prefix='',
        s3_bucket_out=None):
    """
    Write `s3_object_names` from bucket `s3_bucket_in` to `tar_gz_object` in
    `s3_bucket_out`, or `s3_bucket_in` if `s3_bucket_out` is not specified.
    """
    tar_internal_prefix = '' if tar_internal_prefix is None else tar_internal_prefix
    logger.info(
        f's3_objects_to_s3_tar_gz_file: start: s3_bucket_in={s3_bucket_in} '
        f's3_object_names={s3_object_names} tar_gz_object={tar_gz_object} '
        f's3_bucket_out={s3_bucket_out} tar_internal_prefix={tar_internal_prefix}')
    
    # Track the tar.gz archive's objects
    tar_items = []

    # Initialise for tar.gz
    tar_stream = io.BytesIO()
    tar = tarfile.open(mode='w:gz', fileobj=tar_stream)

    # Get each s3 object, write it to tar.gz with required name and size info
    s3_client = boto3.client('s3')
    
    try:
        for s3_object_name in s3_object_names:
            object_name = f'{tar_internal_prefix}{os.path.basename(s3_object_name)}'
            logger.info(f's3_object_name={s3_object_name} object_name={object_name}')
            try:
                s3_object = s3_client.get_object(Bucket=s3_bucket_in, Key=s3_object_name)
            except s3_client.exceptions.NoSuchKey as e:
                logger.error(str(e))
                raise common_lib.S3LibError(
                        f'Unable to find key "{s3_object_name}" in '
                        f'bucket "{s3_bucket_in}". {str(e)}')
            # Determine file name inside tar, and its size
            tar_info = tarfile.TarInfo(object_name)
            tar_info.size = s3_object['ContentLength']
            tar.addfile(tar_info, io.BytesIO(s3_object['Body'].read()))
            tar_items.append({'name': object_name, 'size': tar_info.size})
    finally:
        logger.info('tar.close()')
        tar.close()

    # Write the tar object to s3
    s3_bucket_out = s3_bucket_in if s3_bucket_out is None else s3_bucket_out
    logger.info(
        f's3_client.put_object s3_bucket_out={s3_bucket_out} '
        f'tar_gz_object={tar_gz_object}')

    s3_client.put_object(
        Body=tar_stream.getvalue(),
        Bucket=s3_bucket_out,
        Key=tar_gz_object)

    logger.info('s3_objects_to_s3_tar_gz_file: return')
    return tar_items