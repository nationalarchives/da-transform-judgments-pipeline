#!/usr/bin/env python3
import logging
import boto3  # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/index.html
import tarfile  # https://docs.python.org/3/library/tarfile.html
import io

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
