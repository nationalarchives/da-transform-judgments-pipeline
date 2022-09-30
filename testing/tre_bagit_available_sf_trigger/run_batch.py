#!/usr/bin/env python3
"""
Send a number of TRE `bagit-available` events in rapid succession using either
a local tre-vb-trigger function, or one deployed to AWS via SNS topic tre-in.

The script does not currently verify the executions complete successfully,
only that they submit successfully for viewing in the AWS console.

If the --sns arg is given, execution is via SNS topic ${env}-tre-in. In this
case the forwarding lambda deployed to AWS will be invoked to start the
Validate BagIt Step Function.

If the --sns arg is omitted, a local import of tre_vb_trigger is used to
execute the Step Function. PYTHONPATH must be set to point to this.

Execution examples are provided in the accompanying README.md.
"""
import concurrent.futures
import logging
import argparse
import json
from datetime import datetime, timezone
from aws_test_lib.aws_tester import AWSTester
from tre_event_lib import tre_event_api
import time
import uuid

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


def sns_publish(
    at_deployment: AWSTester,
    topic_name: str,
    message: str
):
    ns = time.time_ns()
    logger.info('submit_sns nS: %s', ns)
    return at_deployment.sns_publish(
        topic_name=topic_name,
        message=message)


def main(
        aws_profile_management: str,
        aws_profile_deployment: str,
        environment_name: str,
        test_consignment_ref: str,
        test_consignment_type: str,
        test_consignment_s3_bucket: str,
        test_consignment_archive_s3_path: str,
        test_consignment_checksum_s3_path: str,
        message_count: int,
        use_sns: bool,
        empty_event: bool,
        incomplete_event: bool
):
    """
    Submit `message_count` events to SNS topic `environment`-tre-in.
    """
    logger.info('main: aws_profile_management=%s aws_profile_deployment=%s '
        'environment_name=%s test_consignment_s3_bucket=%s '
        'test_consignment_archive_s3_path=%s '
        'test_consignment_checksum_s3_path=%s test_consignment_ref=%s '
        'message_count=%s sns_publish=%s',
        aws_profile_management, aws_profile_deployment, environment_name,
        test_consignment_s3_bucket, test_consignment_archive_s3_path,
        test_consignment_checksum_s3_path, test_consignment_ref,
        message_count, sns_publish)

    at_management = AWSTester(aws_profile=aws_profile_management)
    at_deployment = AWSTester(aws_profile=aws_profile_deployment)
    tre_in_topic = f'{environment_name}-tre-in'  # deployment account

    # Generate required number of bagit-available test events
    logger.info(SEPARATOR)
    message_list = []
    for _ in range(message_count):
        if empty_event or incomplete_event:
            malformed_event = {}
            if incomplete_event:
                malformed_event[tre_event_api.KEY_UUIDS] = []
                malformed_event[tre_event_api.KEY_UUIDS].append(
                    {'test-UUID': str(uuid.uuid4())}
                )

            message_list.append(json.dumps(malformed_event))
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

    if use_sns:
        # Send prepared bagit-available events to the tre-in SNS topic
        with concurrent.futures.ThreadPoolExecutor() as executor:
            logger.info('executor max_workers: %s', executor._max_workers)
            futures_dict = {
                executor.submit(
                    sns_publish,
                    at_deployment,
                    tre_in_topic,
                    message
                ): message for message in message_list
            }

            logger.info('futures_dict: %s', futures_dict)

            for future in concurrent.futures.as_completed(futures_dict):
                logger.info('future: %s', future)
                logger.info('future.result(): %s', future.result())
    else:
        # Run Validate BagIt handler locally with bagit-available events
        import tre_vb_trigger
        simulated_input_records = []
        
        for test_event_json in message_list:
            body_json = json.dumps(
                {
                    'Message': test_event_json
                }
            )

            simulated_input_records.append(
                {
                    'eventSourceARN': 'arn:aws:sqs:example:00example000:local-test',
                    'body': body_json
                }
            )

        simulated_input = {
            'Records': simulated_input_records
        }

        local_result = tre_vb_trigger.handler(
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
            'Send a number of TRE `bagit-available` events in rapid '
            'succession using either a local tre-vb-trigger function, or one '
            'deployed to AWS via SNS topic tre-in. Optionally send invalid '
            'events.'))

    parser.add_argument('--aws_profile_management', type=str, required=True,
        help='AWS_PROFILE name for management account (test data source)')
    parser.add_argument('--aws_profile_deployment', type=str, required=True,
        help='AWS_PROFILE name for deployment account (where test runs)')
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
    parser.add_argument('--sns', action='store_true',
        help='Send messages to SNS instead of running locally')
    
    invalid_event_group = parser.add_mutually_exclusive_group()
    invalid_event_group.add_argument('--empty_event', action='store_true',
        help='Send an empty TRE event instead of a valid one')
    invalid_event_group.add_argument('--incomplete_event', action='store_true',
        help='Send an empty TRE event instead of a valid one')
    
    invalid_event_group.set_defaults(
        empty_event=False,
        incomplete_event=False
    )
    
    parser.set_defaults(sns=False)

    args = parser.parse_args()

    main(
        aws_profile_management=args.aws_profile_management,
        aws_profile_deployment=args.aws_profile_deployment,
        environment_name=args.environment_name,
        test_consignment_ref=args.test_consignment_ref,
        test_consignment_type=args.test_consignment_type,
        test_consignment_s3_bucket=args.test_consignment_s3_bucket,
        test_consignment_archive_s3_path=args.test_consignment_archive_s3_path,
        test_consignment_checksum_s3_path=args.test_consignment_checksum_s3_path,
        message_count=args.message_count,
        use_sns=args.sns,
        empty_event=args.empty_event,
        incomplete_event=args.incomplete_event
    )
    