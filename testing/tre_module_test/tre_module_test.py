import logging
import sys
import json
from test_consignment import TestConsignment
from consignment_tester import ConsignmentTester
from environment import Environment
from tests.test_tdr_bagit_retry import test_tdr_bagit_retry
from tests.test_tdr_bagit_function_error import test_tdr_bagit_function_error
from tests.test_tdr_files_retry import test_tdr_files_retry
from tests.test_parser_error_path import test_parser_error_path
from tests.test_editorial_retry import test_editorial_retry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)


def main(s3_data_bucket, environment_file, consignment_file, aws_profile_data=None, aws_profile_env=None):
    """
    s3_data_bucket          : Name of S3 bucket holding test data files
    environment_file        : Name of config file for test environment
    consignment_file        : Name of config file describing test consignments
    aws_profile_data        : AWS profile to locate test data files; defaults to AWS_PROFILE
    aws_profile_env         : AWS profile to access environment to test; defaults to aws_profile_data
    """
    logger.info(f'main: s3_data_bucket={s3_data_bucket} '
        f'environment_file={environment_file} '
        f'consignment_file={consignment_file} '
        f'aws_profile_data={aws_profile_data} '
        f'aws_profile_env={aws_profile_env}')

    config = None
    with open(environment_file) as f:
        config = Environment(json.load(f))

    ct = ConsignmentTester(
        s3_data_bucket=s3_data_bucket,
        environment=config,
        aws_profile_data=aws_profile_data,
        aws_profile_env=aws_profile_env)

    test_consignments = None
    with open(consignment_file) as f:
        test_consignments = json.load(f)
    
    tc_shared_consignment = TestConsignment(config=test_consignments['shared-consignment'])
    tc_bagit_retry = TestConsignment(config=test_consignments['test-bagit-retry'])
    tc_files_retry = TestConsignment(config=test_consignments['test-files-retry'])
    tc_parser_error = TestConsignment(config=test_consignments['test-parser-error'])

    test_editorial_retry(ct=ct, tc=tc_shared_consignment)  # good 1st test as also runs test_ok_path.py
    test_tdr_bagit_retry(ct=ct, tc=tc_bagit_retry)
    test_tdr_bagit_function_error(ct=ct)  # no tc param; uses malformed message to deliberately fail
    test_tdr_files_retry(ct=ct, tc=tc_files_retry)
    test_parser_error_path(ct=ct, tc=tc_parser_error)
    # test_tdr_duplicate_resend_parallel(ct=ct, tc=tc_shared_consignment)

    logger.info('###########################################################')
    logger.info('#                 All tests completed OK                  #')
    logger.info('###########################################################')


if __name__ == "__main__":
    if (len(sys.argv) < 4) or (len(sys.argv) > 6):
        raise ValueError('Usage: s3_data_bucket environment_file consignment_file '
            '[aws_profile_data] [aws_profile_env]')

    main(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        None if len(sys.argv) < 5 else sys.argv[4],
        None if len(sys.argv) < 6 else sys.argv[5]
    )
