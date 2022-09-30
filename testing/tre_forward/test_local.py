#!/usr/bin/env python3
"""
Simulate receipt of a number of TRE `bagit-available` events.
"""
import logging
import argparse
import uuid
import json
from aws_test_lib.aws_tester import AWSTester
from tre_event_lib import tre_event_api

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)

SOURCE_PRODUCER = 'test-producer'
SOURCE_PROCESS = 'test-process'
SEPARATOR = '#' * 80


def create_bagit_available_event_json(
        at_management: AWSTester,
        environment_name: str,
        test_consignment_ref: str,
        test_consignment_type: str,
        test_consignment_s3_bucket: str,
        test_consignment_archive_s3_path: str,
        test_consignment_checksum_s3_path: str
) -> str:
    """
    Return a `bagit-available` event as a JSON string, with values derived
    from the supplied parameters. The helper object `at_management` is used to
    generate valid pre-signed URLs for the given S3 objects (i.e. the BagIt
    archive and BagIt archive checksum files).
    """
    EVENT_BAGIT_AVAILABLE = 'bagit-available'

    # Create pre-signed URLs for BagIt tar.gz and tar.gz.sha256
    source_tar_gz_url = at_management.get_presigned_url(
        bucket=test_consignment_s3_bucket,
        key=test_consignment_archive_s3_path
    )

    source_checksum_url = at_management.get_presigned_url(
        bucket=test_consignment_s3_bucket,
        key=test_consignment_checksum_s3_path
    )

    # Create event's parameters block
    parameters_block = {
        EVENT_BAGIT_AVAILABLE: {
            'resource': {
                'resource-type': 'Object',
                'access-type': 'url',
                'value': source_tar_gz_url
            },
            'resource-validation': {
                'resource-type': 'Object',
                'access-type': 'url',
                'value': source_checksum_url,
                'validation-method': 'sha256'
            },
            'reference': test_consignment_ref
        }
    }

    # Create the event and convert this to JSON
    bagit_available_event = tre_event_api.create_event(
        consignment_type=test_consignment_type,
        environment=environment_name,
        producer=SOURCE_PRODUCER,
        process=SOURCE_PROCESS,
        event_name=EVENT_BAGIT_AVAILABLE,
        prior_event=None,
        parameters=parameters_block)


    logger.info('bagit_available_event: %s', bagit_available_event)
    bagit_available_event_json = json.dumps(bagit_available_event)
    logger.info('bagit_available_event_json: %s', bagit_available_event_json)
    return bagit_available_event_json


def main(
        aws_profile_management: str,
        environment_name: str,
        test_consignment_ref: str,
        test_consignment_type: str,
        test_consignment_s3_bucket: str,
        test_consignment_archive_s3_path: str,
        test_consignment_checksum_s3_path: str,
        message_count: int,
        empty_event: bool,
        omit_message_attributes: bool
):
    """
    Submit `message_count` events to SNS topic `environment`-tre-in.
    """
    logger.info('main: aws_profile_management=%s '
        'environment_name=%s test_consignment_s3_bucket=%s '
        'test_consignment_archive_s3_path=%s '
        'test_consignment_checksum_s3_path=%s test_consignment_ref=%s '
        'message_count=%s',
        aws_profile_management, environment_name,
        test_consignment_s3_bucket, test_consignment_archive_s3_path,
        test_consignment_checksum_s3_path, test_consignment_ref,
        message_count)

    at_management = AWSTester(aws_profile=aws_profile_management)

    # Generate required number of bagit-available test events
    logger.info(SEPARATOR)
    message_list = []
    for _ in range(message_count):
        if empty_event:
            message_list.append(json.dumps({}))
        else:
            message_list.append(
                create_bagit_available_event_json(
                    at_management=at_management,
                    environment_name=environment_name,
                    test_consignment_ref=test_consignment_ref,
                    test_consignment_type=test_consignment_type,
                    test_consignment_s3_bucket=test_consignment_s3_bucket,
                    test_consignment_archive_s3_path=test_consignment_archive_s3_path,
                    test_consignment_checksum_s3_path=test_consignment_checksum_s3_path
                )
            )
    
    logger.info('len(message_list)=%s', len(message_list))

    # Run Validate BagIt handler locally with bagit-available events
    import tre_forward
    simulated_input_records = []
    
    for test_event_json in message_list:
        body_dict = {
            'Message': test_event_json
        }

        if not omit_message_attributes:
            body_dict['MessageAttributes'] = {}

        simulated_input_records.append(
            {
                'eventSourceARN': 'arn:aws:sqs:example:00example000:local-test',
                'body': json.dumps(body_dict)
            }
        )

    simulated_input = {
        'Records': simulated_input_records
    }

    local_result = tre_forward.lambda_handler(
        event=simulated_input,
        context=None
    )
    
    logger.info('local_result=%s', local_result)


if __name__ == "__main__":
    """
    Process CLI arguments and invoke main method.
    """
    parser = argparse.ArgumentParser(
        description=(
            'Submit a batch of TRE `bagit-available` events to the local '
            'tre_forward handler.')
    )

    parser.add_argument('--aws_profile_management', type=str, required=True,
        help='AWS_PROFILE name for management account (test data source)')
    parser.add_argument('--environment_name', type=str, required=True,
        help='Name of environment being tested; e.g. dev, test, int, ...')
    parser.add_argument('--test_consignment_s3_bucket', type=str, required=True,
        help='The s3 bucket holding the test consignment to use for the test')
    parser.add_argument('--test_consignment_archive_s3_path', type=str,
        required=True, help='S3 path of the test consignment archive (tar.gz)')
    parser.add_argument('--test_consignment_checksum_s3_path', type=str,
        required=True,
        help='S3 path of the test consignment checksum (tar.gz.sha256)')
    parser.add_argument('--test_consignment_ref', type=str, required=True,
        help='The consignment reference to use for the tests')
    parser.add_argument('--test_consignment_type', type=str, default='judgment',
        help='The consignment reference type for the event')
    parser.add_argument('--message_count', type=int, required=True,
        help='Number of messages to attempt to send simultaneously')
    
    invalid_event_group = parser.add_argument_group()
    invalid_event_group.add_argument('--empty_event', action='store_true',
        help='Send an empty TRE event instead of a valid one')
    invalid_event_group.add_argument('--omit_message_attributes', action='store_true',
        help='Do not include SNS MessageAttribute block')
    
    invalid_event_group.set_defaults(
        empty_event=False,
        incomplete_event=False
    )
    
    args = parser.parse_args()

    main(
        aws_profile_management=args.aws_profile_management,
        environment_name=args.environment_name,
        test_consignment_ref=args.test_consignment_ref,
        test_consignment_type=args.test_consignment_type,
        test_consignment_s3_bucket=args.test_consignment_s3_bucket,
        test_consignment_archive_s3_path=args.test_consignment_archive_s3_path,
        test_consignment_checksum_s3_path=args.test_consignment_checksum_s3_path,
        message_count=args.message_count,
        empty_event=args.empty_event,
        omit_message_attributes=args.omit_message_attributes
    )
