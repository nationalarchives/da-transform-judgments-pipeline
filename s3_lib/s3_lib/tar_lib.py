#!/usr/bin/env python3
import logging
import boto3  # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/index.html
import tarfile  # https://docs.python.org/3/library/tarfile.html
import io

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def untar_s3_object(input_bucket_name, object_name, output_bucket_name=None):
    """
    Perform an untar operation on the specified s3 `object_name` in
    `input_bucket_name`; untar to `input_bucket_name` unless
    `output_bucket_name` is provided.
    """
    logger.info('untar start')
    output_bucket_name = input_bucket_name if output_bucket_name is None else output_bucket_name
    s3_client = boto3.client('s3')
    s3_input_object = s3_client.get_object(Bucket=input_bucket_name, Key=object_name)
    tar_stream = io.BytesIO(s3_input_object['Body'].read())

    with tarfile.open(fileobj=tar_stream) as tar_content:
        for item in tar_content:
            logger.info(f'item.isdir()={item.isdir()} item.isFile()={item.isfile()} item.name={item.name} item={item}')
            if item.isfile():
                # Use tmp_name as item.name.removeprefix('./')) requires Python >= 3.9
                tmp_name = item.name[2:] if item.name.startswith('./') else item.name
                item_stream = tar_content.extractfile(item).read()
                s3_client.upload_fileobj(
                    io.BytesIO(item_stream),
                    Bucket=output_bucket_name,
                    Key=tmp_name)

    logger.info('untar end')
