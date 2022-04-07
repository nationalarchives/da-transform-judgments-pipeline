#!/usr/bin/env python3
import logging
import requests  # https://docs.python-requests.org/en/master/api/
import hashlib  # https://docs.python.org/3/library/hashlib.html
import boto3  # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/index.html
import codecs

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

READ_BLOCK_SIZE = 5 * 1024 * 1024  # s3 multipart min=5MB, except "last" part
ENCODING_UTF8 = 'utf-8'
S3_PATH_SEPARATOR = '/'

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

def get_max_s3_subfolder_number(bucket_name, object_filter):
    """
    Return the max numeric folder name below path `s3_object_prefix` in
    `s3_bucket`, or `None` if no numeric child folders are found.

    For example, given the following list of objects in s3 bucket `foo`,
    `get_max_s3_subfolder_number('foo', 'alpha/bravo/)` would return `1`:

    * alpha/bravo/0/charlie
    * alpha/bravo/0/delta
    * alpha/bravo/1/echo/foxtrot
    * alpha/bravo/golf/hotel
    * india/juliet/kilo/lima

    Calling 
    """
    logger.info(
        f'get_max_s3_subfolder_number start: bucket_name="{bucket_name}" '
        f'object_filter="{object_filter}"')
    
    s3_resource = boto3.resource('s3')
    s3_bucket = s3_resource.Bucket(bucket_name)
    s3_object_list = list(s3_bucket.objects.filter(Prefix=object_filter))
    logger.info(f's3_object_list={s3_object_list}')
    numeric_subfolders = [
        o.key[len(object_filter):].split(S3_PATH_SEPARATOR, 1)[0]
        for o in s3_object_list
        if o.key[len(object_filter):].split(S3_PATH_SEPARATOR, 1)[0].isdigit()
    ]
    logger.info(f'numeric_subfolders={numeric_subfolders}')
    logger.info(f'get_max_s3_subfolder_number return: numeric_subfolders={numeric_subfolders}')
    return max(numeric_subfolders) if len(numeric_subfolders) > 0 else None

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
        raise_error_if_object_exists(target_bucket_name, target_object_name)

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

def string_to_s3_object(
        string,
        target_bucket_name,
        target_object_name,
        allow_overwrite=False):
    """
    Copy the content of the supplied `string` into an object with name
    `target_object_name` in bucket `target_bucket_name'.
    """
    logger.info(
            f'string_to_s3_object start: string="{string}" '
            f'target_bucket_name="{target_bucket_name}" '
            f'target_object_name="{target_object_name}" '
            f'allow_overwrite="{allow_overwrite}"')

    # Unless allow_overwrite is True, don't copy object if it already exists 
    if not allow_overwrite:
        raise_error_if_object_exists(target_bucket_name, target_object_name)

    s3r = boto3.resource('s3')
    s3r.Object(target_bucket_name, target_object_name).put(Body=string)
    logger.info('string_to_s3_object end')

def raise_error_if_object_exists(bucket, object):
    """
    Raise a ValueError if `object` exists in `bucket`.
    """
    logger.info(
            f'raise_error_if_object_exists start: checking "{object}" does '
            f'not already exist in "{bucket}"')
    
    if s3_object_exists(bucket, object):
        raise ValueError(
                f'Copy not allowed; "{object}" already exists in bucket '
                f'"{bucket}"')

    logger.info('raise_error_if_object_exists end')

def s3_object_to_dictionary(s3_bucket, s3_key, separator=':'):
    """
    Split each line in s3 object `s3_key' in `s3_bucket` using the left-most
    `separator`.
    """
    logger.info(f's3_object_to_dictionary start: s3_bucket={s3_bucket} s3_key={s3_key}')
    dictionary = {}
    s3_client = boto3.client('s3')
    s3o = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    reader = codecs.getreader(ENCODING_UTF8)
    for line in reader(s3o['Body']):
        columns = line.rstrip().split(separator, 1)
        if len(columns) > 0:
            key = columns[0].strip()
            value = None if len(columns) < 2 else columns[1].strip()
            dictionary[key] = value
    logger.info('s3_object_to_dictionary return')
    return dictionary

def get_s3_object_presigned_url(bucket, key, expiry):
    """
    Return a preshared URL for `key` in `bucket` with the specified
    `expiration` seconds.
    """
    logger.info(
        f'get_s3_object_presigned_url start: bucket={bucket} '
        f'key={key} expiry={expiry}')
    s3c = boto3.client('s3')
    logger.info(f'get_s3_object_presigned_url return')
    return s3c.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=expiry
    )
