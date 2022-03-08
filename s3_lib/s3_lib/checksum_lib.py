#!/usr/bin/env python3
import logging
import requests
import os
import boto3  # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/index.html
import hashlib  # https://docs.python.org/3/library/hashlib.html

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

READ_BLOCK_SIZE = 5 * 1024 * 1024  # s3 multipart min=5MB, except "last" part
ENCODING_UTF8 = 'utf-8'
ITEM_FILE = 'file'
ITEM_BASENAME = 'basename'
ITEM_CHECKSUM = 'checksum'

def checksum_item(file, basename, checksum):
    """
    Creates a dictionary object to represent an item and its checksum.
    """
    return {
        ITEM_FILE: file,
        ITEM_BASENAME: basename,
        ITEM_CHECKSUM: checksum
    }

def get_manifest_url(url):
    """
    Return a list of dictionary items from a URL (with each item having a
    filename, basename and checksum).
    """
    logger.info('get_manifest_url start')
    response = requests.get(url, stream=True)
    if not response.ok:
        raise ValueError(
            f'Failed to open checksum manifest: response.status_code='
            f'{response.status_code} : {response.text}')

    checksums = []
    for line in response.iter_lines():
        line_decoded = line.decode(ENCODING_UTF8)
        checksum = line_decoded[0:64]
        file = line_decoded[64:].strip()
        basename = os.path.basename(file)
        checksums.append(checksum_item(file, basename, checksum))
    
    logger.debug(f'checksums={checksums}')
    logger.info('get_manifest_url end')
    return checksums

def get_manifest_s3(bucket_name, object_name):
    """
    Return a list of dictionary items from an AWS s3 object (with each item
    having a filename, basename and checksum).
    """
    logger.info(
        f'get_manifest_object start: bucket_name={bucket_name} '
        f'object_name={object_name}')

    s3_client = boto3.client('s3')
    s3_object = s3_client.get_object(Bucket=bucket_name, Key=object_name)
    checksums = []

    for line in s3_object['Body'].iter_lines():
        line_decoded = line.decode(ENCODING_UTF8)
        checksum = line_decoded[0:64]
        file = line_decoded[64:].strip()
        basename = os.path.basename(file)
        checksums.append(checksum_item(file, basename, checksum))
    
    logger.debug(f'checksums={checksums}')
    logger.info('get_manifest_object end')
    return checksums

def verify_s3_object_checksum(bucket_name, object_name, expected_checksum):
    """
    Calculate the SHA 256 checksum of `object_name` in `bucket_name` and
    confirm the checksum matches `expected_checsum`; if it does not match, a
    ValueError is raised.
    """
    logger.info('verify_checksum start')

    s3_client = boto3.client('s3')
    s3_object = s3_client.get_object(Bucket=bucket_name, Key=object_name)
    hashlib_sha256 = hashlib.sha256()
    stream = s3_object['Body']._raw_stream
    chunk = stream.read(READ_BLOCK_SIZE)
    logger.debug(f'len(chunk)={len(chunk)}')
    while chunk != b'':
        logger.debug(f'len(chunk)={len(chunk)}')
        hashlib_sha256.update(chunk)
        chunk = stream.read(READ_BLOCK_SIZE)

    hex_digest = hashlib_sha256.hexdigest()
    if hex_digest != expected_checksum:
        raise ValueError(
            f'Calculated checksum "{hex_digest}" does not match expected '
            f'checksum "{expected_checksum}" for object "{object_name}" in '
            f'bucket "{bucket_name}"')
    logger.info(
        f'Calculated checksum "{hex_digest}" matches expected checksum '
        f'"{expected_checksum}" for object "{object_name}" in bucket '
        f'"{bucket_name}"')

    logger.info('verify_checksum end')

def verify_s3_manifest_checksums(bucket_name, bagit_name):
    """
    Load the expected checksums from the manifest files located in
    `bucket_name`/`bagit_name`, then verify the file checksums in the manifest
    match the checksums calculated from the corresponding files located in
    `bucket_name`/`bagit_name`.
    """
    logger.info('verify_s3_manifest_checksums start')
    tag_manifest_object = f'{bagit_name}/tagmanifest-sha256.txt'
    data_manifest_object = f'{bagit_name}/manifest-sha256.txt'
    tag_manifest_checksums = get_manifest_s3(bucket_name, tag_manifest_object)
    data_manifest_checksums = get_manifest_s3(bucket_name, data_manifest_object)
    checked_files = {
        'path': bagit_name,
        'root': [],
        'data': []
    }

    logger.info(f'Validating {tag_manifest_object}')
    for item in tag_manifest_checksums:
        validation_object = f'{bagit_name}/{item[ITEM_FILE]}'
        checked_files['root'].append(validation_object)
        logger.info(f'root item={item} validation_object={validation_object}')
        verify_s3_object_checksum(bucket_name, validation_object, item[ITEM_CHECKSUM])
    
    logger.info(f'Validating {data_manifest_object}')
    for item in data_manifest_checksums:
        validation_object = f'{bagit_name}/{item[ITEM_FILE]}'
        checked_files['data'].append(validation_object)
        logger.info(f'data item={item} validation_object={validation_object}')
        verify_s3_object_checksum(bucket_name, validation_object, item[ITEM_CHECKSUM])

    logger.info('verify_s3_manifest_checksums return')
    return checked_files
