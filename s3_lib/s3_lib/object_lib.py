#!/usr/bin/env python3
import logging
import requests  # https://docs.python-requests.org/en/master/api/
import hashlib  # https://docs.python.org/3/library/hashlib.html
import boto3  # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/index.html

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

READ_BLOCK_SIZE = 5 * 1024 * 1024  # s3 multipart min=5MB, except "last" part

def s3_object_exists(bucket_name, object_filter):
    """
    Return `True` if `object_filter` in `bucket_name`, otherwise `False`.
    """
    logger.info(
            f's3_object_exists start: bucket_name="{bucket_name}" '
            f'object_filter="{object_filter}"')
    
    s3_resource = boto3.resource('s3')
    s3_bucket = s3_resource.Bucket(bucket_name)
    s3_object_list = list(s3_bucket.objects.filter(Prefix=object_filter))
    logger.info(f's3_object_exists return: s3_object_list={s3_object_list}')
    return len(s3_object_list) > 0

def s3_ls(bucket_name, object_filter):
    """
    Return list of objects in `bucket_name` that match `object_filter`.
    """
    logger.info(
            f's3_object_ls start: bucket_name="{bucket_name}" '
            f'object_filter="{object_filter}"')
    
    s3_resource = boto3.resource('s3')
    s3_bucket = s3_resource.Bucket(bucket_name)
    s3_objects = s3_bucket.objects.filter(Prefix=object_filter)
    s3_object_list = []
    for s3_object in s3_objects:
        s3_object_list.append(s3_object.key)
    logger.info(f's3_object_ls return: s3_bucket_list={s3_object_list}')
    return s3_object_list

def url_to_s3_object(
        source_url,
        target_bucket_name,
        target_object_name,
        allow_overwrite=False,
        expected_checksum=None):
    """
    Copy the content of the supplied `source_url` into an object with name
    `target_object_name` in bucket `target_bucket_name'.

    The `expected_checksum` can be validated during or the copy
    process; checksum validation failure will raise a `ValueException`.
    """
    logger.info(
            f'copy_url_data_to_bucket start: source_url="{source_url}" '
            f'target_bucket_name="{target_bucket_name}" '
            f'target_object_name="{target_object_name}" '
            f'allow_overwrite="{allow_overwrite}" '
            f'expected_checksum="{expected_checksum}"')

    # Unless allow_overwrite is True, don't copy object if it already exists 
    if not allow_overwrite:
        logger.info(
                f'Checking s3 object "{target_object_name}" does not already '
                f'exist in bucket "{target_bucket_name}"')
        if s3_object_exists(target_bucket_name, target_object_name):
            raise ValueError(
                    f'Copy not allowed; "{target_object_name}" already '
                    f'exists in bucket "{target_bucket_name}"')

    response = requests.get(source_url, stream=True)

    if not response.ok:
        raise ValueError(
            f'Failed to open source URL "{source_url}" : '
            f'response.status_code={response.status_code} : {response.text}')

    hashlib_sha256 = hashlib.sha256()

    # Initiate s3 session
    s3_session = boto3.session.Session()
    s3_session_resource = s3_session.resource('s3')
    s3_target_object = s3_session_resource.Object(target_bucket_name, target_object_name)
    s3_uploader = s3_target_object.initiate_multipart_upload()

    S3_KEY_PARTS = 'Parts'
    S3_KEY_PART_NUMBER = 'PartNumber'
    S3_KEY_ETAG = 'ETag'
    s3_parts = {S3_KEY_PARTS: []}
    s3_part_count = 0
    
    logger.info('Starting multipart upload and checksum validation')
    try:
        for chunk in response.iter_content(chunk_size=READ_BLOCK_SIZE):
            s3_part_count += 1
            s3_uploader_part = s3_uploader.Part(s3_part_count)
            s3_part_response = s3_uploader_part.upload(Body=chunk)
            s3_parts[S3_KEY_PARTS].append(
                {
                    S3_KEY_PART_NUMBER: s3_part_count,
                    S3_KEY_ETAG: s3_part_response[S3_KEY_ETAG]
                })
            
            logger.debug(
                f'Multipart upload part {s3_part_count} sent, '
                f'ETag={s3_part_response[S3_KEY_ETAG]}')
            
            if expected_checksum is not None:
                hashlib_sha256.update(chunk)
                logger.debug(f'Hash updated')

        logger.info(f'Send multipart upload complete notification')
        s3_uploader_result = s3_uploader.complete(MultipartUpload=s3_parts)
        logger.debug(f's3_uploader_result={s3_uploader_result}')
        if expected_checksum is not None:
            hex_digest = hashlib_sha256.hexdigest()
            logger.info(f'hexdigest         : "{hex_digest}"')
            logger.info(f'expected_checksum : "{expected_checksum}"')
            if hex_digest != expected_checksum:
                raise ValueError(
                    f'Invalid checksum; calculated "{hex_digest}" but '
                    f'expected "{expected_checksum}" for URL {source_url}')        
    except Exception as e:
        logger.error(f'Error in copy_url_data_to_bucket: {e}')
        logger.exception(e)
        logger.info('Abort multipart upload...')
        s3_uploader.abort()
        logger.debug('Multipart upload abort complete')
        raise e

    logger.info('copy_url_data_to_bucket end')
