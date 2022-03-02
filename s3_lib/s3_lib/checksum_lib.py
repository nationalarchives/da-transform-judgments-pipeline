#!/usr/bin/env python3
import logging
import requests
import os
import boto3  # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/index.html
import hashlib  # https://docs.python.org/3/library/hashlib.html

logger = logging.getLogger(__name__)

READ_BLOCK_SIZE = 5 * 1024 * 1024  # s3 multipart min=5MB, except "last" part
ENCODING_UTF8 = 'utf-8'
ITEM_FILE = 'file'
ITEM_BASENAME = 'basename'
ITEM_CHECKSUM = 'checksum'

def checksum_item(file, basename, checksum):
    return {
        ITEM_FILE: file,
        ITEM_BASENAME: basename,
        ITEM_CHECKSUM: checksum
    }

def get_manifest_url(url):
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
    logger.info(f'hexdigest         : "{hex_digest}"')
    logger.info(f'expected_checksum : "{expected_checksum}"')
    if hex_digest != expected_checksum:
        raise ValueError(
            f'Invalid checksum; calculated "{hex_digest}" but expected '
            f'"{expected_checksum}" for object "{object_name}" in bucket '
            f'"{bucket_name}"')
    logger.info('verify_checksum end')

def verify_s3_manifest_checksums(bucket_name, bagit_name):
    logger.info('verify_s3_manifest_checksums start')
    tag_manifest_object = f'{bagit_name}/tagmanifest-sha256.txt'
    data_manifest_object = f'{bagit_name}/manifest-sha256.txt'
    tag_manifest_checksums = get_manifest_s3(bucket_name, tag_manifest_object)
    data_manifest_checksums = get_manifest_s3(bucket_name, data_manifest_object)

    logger.info(f'Validating {tag_manifest_object}')
    for item in tag_manifest_checksums:
        validation_object = f'{bagit_name}/{item[ITEM_FILE]}'
        logger.info(f'item={item} validation_object={validation_object}')
        verify_s3_object_checksum(bucket_name, validation_object, item[ITEM_CHECKSUM])
    
    logger.info(f'Validating {data_manifest_object}')
    for item in data_manifest_checksums:
        validation_object = f'{bagit_name}/{item[ITEM_FILE]}'
        logger.info(f'item={item} validation_object={validation_object}')
        verify_s3_object_checksum(bucket_name, validation_object, item[ITEM_CHECKSUM])

    logger.info('verify_s3_manifest_checksums end')
