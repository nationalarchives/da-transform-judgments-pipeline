#!/usr/bin/env python3
"""
Update a Step Function's Lambda Function versions in AWS parameter store to be
the respective version.sh file versions, but only if a version has been
increased; the Step Function's version is incremented if one or more Lambda
Function versions change.

usage: update_sf_lambda_versions.py [-h] [--aws_profile AWS_PROFILE] 
        parameter step_function_version_key lambda_versions_key
        lambda_functions_dir

positional arguments:
  parameter                     AWS Parameter Store parameter name
  step_function_version_key     Step Function version block key
  lambda_versions_key           Lambda version block key
  lambda_functions_dir          Path to lambda_functions dir

optional arguments:
  -h, --help                    show this help message and exit
  --aws_profile AWS_PROFILE     AWS_PROFILE to use
"""
import logging
import argparse
import os
import boto3
import json
import glob
from packaging import version


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# Instantiate logger
logger = logging.getLogger(__name__)
LINE = '#' * 70


class AWSSession():
    AWS_PROFILE = 'AWS_PROFILE'

    def __init__(self, aws_profile: str = None):
        logger.info(f'AWSSession __init__ : aws_profile={aws_profile}')

        # Fallback to AWS_PROFILE env var if no AWS profile(s) specified
        if (aws_profile is None) or (len(aws_profile) == 0):
            if (
                (self.AWS_PROFILE in os.environ)
                and
                (len(os.environ[self.AWS_PROFILE]) > 0)
            ):
                aws_profile = os.environ[self.AWS_PROFILE]
            else:
                raise ValueError('AWS profile not specified')

        self.session = boto3.Session(profile_name=aws_profile)
        self.ssm = self.session.client('ssm')

    def get_parameter_store_value(self, parameter: str) -> dict:
        logger.info(f'get_parameter_store_value : parameter={parameter}')
        psv = self.ssm.get_parameter(Name=parameter, WithDecryption=True)
        logger.info(f'psv={psv}')
        return psv

    def put_parameter_store_value(self, parameter: str, value: str) -> dict:
        logger.info(f'put_parameter_store_value : parameter={parameter} '
                    f'value={value}')

        response = self.ssm.put_parameter(
            Name=parameter,
            Value=value,
            Overwrite=True)

        logger.info(f'put_parameter response={response}')


class ImageVersions():
    def __init__(self, lambda_functions_dir: str):
        logger.info('ImageVersions __init__ : '
                    f'lambda_functions_dir={lambda_functions_dir}')

        SEPARATOR = '='
        COMMENT = '#'
        self.lambda_function_dict = {}
        match = f'{lambda_functions_dir}/*/version.sh'
        logger.info(f'match={match}')

        # Process each version.sh file
        for file_path in glob.glob(pathname=match):
            logger.info(f'file_path={file_path}')
            image = None
            tag = None
            with open(file_path, 'rt') as f:
                # Read each property, save only Docker image and tag values
                for line in f:
                    if (not line.startswith(COMMENT)) and (SEPARATOR in line):
                        kv = line.split(sep=SEPARATOR, maxsplit=1)
                        key = kv[0].strip()
                        value = kv[1].strip()
                        logger.info(f'key={key} value={value}')
                        if key == 'docker_image_name':
                            image = value
                        elif key == 'docker_image_tag':
                            tag = value

            if image is not None:
                self.lambda_function_dict[image] = tag

        logger.info(f'self.lambda_function_dict={self.lambda_function_dict}')

    def get_image_version(self, image_name: str) -> str:
        """
        Return image version, or None if it can't be found.
        """
        if image_name in self.lambda_function_dict:
            return self.lambda_function_dict[image_name]

        logger.info(f'No version found for "{image_name}" <- *** MISSING ***')


def increment_version(version_str: str) -> str:
    logger.info(f'increment_version: version_str={version_str}')
    version.Version(version_str)  # checks is valid
    sf_version_aws_list = version_str.split('.')
    logger.info(f'sf_version_aws_list={sf_version_aws_list}')
    if len(sf_version_aws_list) < 3:
        raise ValueError('Version "{version_str}" does not have 3+ parts')
    # Bump the patch/micro number at position 3 (index 2) and re-assemble
    sf_version_aws_list[2] = str(int(sf_version_aws_list[2]) + 1)
    incremented_version = '.'.join(sf_version_aws_list)
    logger.info(f'incremented_version={incremented_version}')
    return incremented_version


def update_sf_lambda_versions(
        parameter: str,
        step_function_version_key: str,
        lambda_versions_key: str,
        lambda_functions_dir: str,
        aws_profile: str = None
):
    logger.info(
        f'update_sf_lambda_versions : parameter={parameter} '
        f'lambda_versions_key={lambda_versions_key} '
        f'lambda_functions_dir={lambda_functions_dir} '
        f'aws_profile={aws_profile}')

    # Get all current image names and versions from disk
    disk_versions = ImageVersions(lambda_functions_dir=lambda_functions_dir)

    # Get current version info from AWS parameter store
    aws = AWSSession(aws_profile=aws_profile)
    pv = aws.get_parameter_store_value(parameter=parameter)
    tf_json = json.loads(pv['Parameter']['Value'])
    logger.info(f'tf_json={tf_json}')

    # Ensure step function version block is present in parameter store record
    if step_function_version_key not in tf_json:
        raise ValueError(f'Step Function version key '
                         f'"{step_function_version_key}" was not found in '
                         f'AWS parameter "{parameter}"')

    sf_version_aws = tf_json[step_function_version_key]
    logger.info(f'sf_version_aws={sf_version_aws}')

    # Ensure lambda version block is present in parameter store record
    if lambda_versions_key not in tf_json:
        raise ValueError(f'Lambda versions key "{lambda_versions_key}" '
                         f'was not found in AWS parameter "{parameter}"')

    lambda_block = tf_json[lambda_versions_key]
    logger.info(f'lambda_block={lambda_block}')

    # Check AWS parameter store record's lambda versions against disk versions
    version_changed = False  # will update step function version & AWS if true
    for lambda_name, lambda_version in lambda_block.items():
        logger.info(f'AWS version info: {lambda_name}={lambda_version}')
        lookup_name = lambda_name.replace('_', '-')  # "_" in AWS, "-" on disk
        disk_version = disk_versions.get_image_version(image_name=lookup_name)
        logger.info(f'Disk version info: {lookup_name}={disk_version}')
        v_aws = version.Version(lambda_version)
        v_disk = None
        if disk_version is not None:
            v_disk = version.Version(disk_version)

        if ((v_disk is not None) and (v_disk > v_aws)):
            logger.info(f'Update for "{lambda_name}": "{lambda_version}" '
                        f'-> "{disk_version}" <- *** UPDATE ***')
            version_changed = True
            logger.info(f'JSON key {lambda_versions_key}.{lambda_name}')
            tf_json[lambda_versions_key][lambda_name] = disk_version
        else:
            warn = ''
            if (v_disk is not None) and (v_disk < v_aws):
                warn = ' <- *** WARNING ***'

            logger.info(f'No update for "{lambda_name}": "{lambda_version}" '
                        f'-> "{disk_version}"{warn}')

    # If any lambda versions updated, update step function version, then AWS
    if version_changed:
        logger.info(f'tf_json={tf_json}')
        sf_version_new = increment_version(sf_version_aws)
        logger.info(f'sf_version_new={sf_version_new} (AWS={sf_version_aws})')
        tf_json[step_function_version_key] = sf_version_new
        logger.info(f'tf_json={tf_json}')
        aws.put_parameter_store_value(
            parameter=parameter,
            value=json.dumps(tf_json, indent=2))

        message = 'Completed OK, versions updated'.center(64)
        logger.info(f'{LINE}')
        logger.info(f'###{message}###')
        logger.info(f'{LINE}')
    else:
        message = 'Completed OK, no changes made'.center(64)
        logger.info(f'{LINE}')
        logger.info(f'###{message}###')
        logger.info(f'{LINE}')


# Parse CLI arguments and pass to entrypoint
parser = argparse.ArgumentParser(description=(
    "Update a Step Function's Lambda Function versions in AWS parameter "
    "store to be the respective version.sh file versions, but only if a "
    "version has been increased; the Step Function's version is incremented "
    "if one or more Lambda Function versions change."))

parser.add_argument('parameter', help='AWS Parameter Store parameter name')
parser.add_argument('step_function_version_key',
                    help='Step Function version block key')
parser.add_argument('lambda_versions_key', help='Lambda version block key')
parser.add_argument('lambda_functions_dir',
                    help='Path to lambda_functions dir')
parser.add_argument('--aws_profile', help='AWS_PROFILE to use')
args = parser.parse_args()

update_sf_lambda_versions(
    parameter=args.parameter,
    step_function_version_key=args.step_function_version_key,
    lambda_versions_key=args.lambda_versions_key,
    lambda_functions_dir=args.lambda_functions_dir,
    aws_profile=args.aws_profile
)
