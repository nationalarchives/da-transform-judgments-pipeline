#!/usr/bin/env python3
"""
Requires the following environment variables be set:
* PARSER_TEST_S3_BUCKET         : S3 bucket holding test docx files
* PARSER_TEST_S3_PATH_DATA_OK   : Path in S3 bucket holding test docx files expected to pass
* PARSER_TEST_S3_PATH_DATA_FAIL : Path in S3 bucket holding test docx files expected to fail
* PARSER_TEST_S3_PATH_OUTPUT    : Path to which parser writes output files in the S3 bucket
* PARSER_TEST_TESTDATA_SUFFIX   : Filter to use only S3 objects that end with this string
* PARSER_TEST_LAMBDA            : The name of the parser lambda function to test
"""
import logging
import os
import boto3
import json
from datetime import datetime, timezone
import uuid


# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_env_var(env_var_name):
    logger.info(f'get_env_var start: env_var_name={env_var_name}')
    if env_var_name not in os.environ:
        raise ValueError(f'Environment variable "{env_var_name}" is not set')
    value = os.environ[env_var_name]
    if len(value) == 0:
        raise ValueError(f'Environment variable "{env_var_name}" is empty')
    logger.info(f'get_env_var return: {env_var_name}={value}')
    return value


class ParserTester():
    init_ts = datetime.now(tz=timezone.utc)

    s3_bucket = get_env_var('PARSER_TEST_S3_BUCKET')
    s3_path_test_data_ok = get_env_var('PARSER_TEST_S3_PATH_DATA_OK')  # e.g. 'parser/ok/'
    s3_path_test_data_fail = get_env_var('PARSER_TEST_S3_PATH_DATA_FAIL')  # e.g. 'parser/fail/'
    s3_path_parser_output = get_env_var('PARSER_TEST_S3_PATH_OUTPUT')  # e.g. 'parser/output/'
    s3_path_parser_output += f'{init_ts.isoformat()}/'  # Group test outputs in timestamped folder
    testdata_suffix = get_env_var('PARSER_TEST_TESTDATA_SUFFIX')  # e.g. '.docx'
    test_lambda = get_env_var('PARSER_TEST_LAMBDA')  # e.g. 'test_judgment_parser'

    s3_presigned_url_expiry = 60
    s3_resource = boto3.resource('s3')
    s3_client = boto3.client('s3')

    def __init__(self):
        s3_bucket = self.s3_resource.Bucket(self.s3_bucket)

        test_docx_files_ok = s3_bucket.objects.filter(Prefix=self.s3_path_test_data_ok)
        self.docx_files_ok = [
            i.key
            for i in test_docx_files_ok
            if i.key.endswith(self.testdata_suffix)
        ]

        test_docx_files_fail = s3_bucket.objects.filter(Prefix=self.s3_path_test_data_fail)
        self.docx_files_fail = [
            i.key
            for i in test_docx_files_fail
            if i.key.endswith(self.testdata_suffix)
        ]


    def generate_presigned_url(self, s3_path):
        logger.info(f'generate_presigned_url: s3_path={s3_path}')
        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.s3_bucket, 'Key': s3_path},
            ExpiresIn=self.s3_presigned_url_expiry)


    def generate_parser_input(self, s3_path: str) -> str:
        ts = datetime.now(tz=timezone.utc)
        consignment_reference = f'{ts.isoformat()}-{uuid.uuid4()}'
        output_path = self.s3_path_parser_output + consignment_reference + '/'

        parser_input = {
            'parser-inputs': {
                'consignment-reference': consignment_reference,
                's3-bucket': self.s3_bucket,
                'document-url': self.generate_presigned_url(s3_path=s3_path),
                'attachment-urls': [],
                's3-output-prefix': output_path
            }
        }

        return json.dumps(parser_input)


    def run_test(self, s3_path: str, expect_parser_error: bool) -> tuple:
        """
        Run test Lambda and return tuple indicating test success and result.
        """
        logger.info(f'run_parser_test start: s3_path={s3_path}')

        s3_client = boto3.client('lambda')
        payload = self.generate_parser_input(s3_path=s3_path)
        logger.info(f'payload={payload}')

        parser_invoke_response = s3_client.invoke(
                FunctionName=self.test_lambda,
                Payload=payload
        )

        logger.info(f'parser_invoke_response={parser_invoke_response}')
        result = json.load(parser_invoke_response['Payload'])
        logger.info(f'result={result}')

        if len(result['parser-outputs']['error-messages']) > 0:
            # Parser reported an error; OK if error was expected
            if expect_parser_error:
                logger.info('Expected parser error')
                return True, result
            else:
                logger.info('Unexpected parser error')
                return False, result
        else:
            # Parser did not report an error; OK if error was not expected
            if expect_parser_error:
                logger.info('Did not get expected parser error')
                return False, result
            else:
                logger.info('Parser ran as expected without error')
                return True, result


    def create_record(
            self,
            s3_path: str,
            result: dict,
            ran_ok: bool,
            expected_parser_error: bool
    ) -> dict:
        return {
            's3_bucket': self.s3_bucket,
            'docx': s3_path,
            'result': result,
            'expected_parser_error': expected_parser_error,
            'ran_ok': ran_ok
        }


    def run_tests(self):
        logger.info('run_tests')

        result_list_test_ok = []
        result_list_test_fail = []

        # Test documents that should pass
        logger.info('Testing documents that should parse successfully')
        for s3_path in self.docx_files_ok:
            ran_ok, result = self.run_test(
                    s3_path=s3_path,
                    expect_parser_error=False)

            record = self.create_record(s3_path=s3_path, result=result, ran_ok=ran_ok, expected_parser_error=False)

            if ran_ok:
                result_list_test_ok.append(record)
            else:
                result_list_test_fail.append(record)

        # Test documents that should fail
        logger.info('Testing documents that should fail to parse')
        for s3_path in self.docx_files_fail:
            ran_ok, result = self.run_test(
                    s3_path=s3_path,
                    expect_parser_error=True)

            record = self.create_record(s3_path=s3_path, result=result, ran_ok=ran_ok, expected_parser_error=True)

            if ran_ok:
                result_list_test_ok.append(record)
            else:
                result_list_test_fail.append(record)

        return result_list_test_ok, result_list_test_fail


def main():
    ts_start = datetime.now(tz=timezone.utc)
    logger.info(f'main start: {ts_start.isoformat()}')
    pt = ParserTester()
    result_list_ok, result_list_fail = pt.run_tests()
    logger.info(f'result_list_ok={result_list_ok}')
    logger.info(f'result_list_fail={result_list_fail}')

    if len(result_list_fail) > 0:
        raise ValueError('Parser test failed; unexpected document result: '
                f'result_list_ok={result_list_ok} '
                f'result_list_fail={result_list_fail}')

    if len(result_list_fail) + len(result_list_ok) == 0:
        raise ValueError('Parser test failed; no documents were tested')

    ts_end = datetime.now(tz=timezone.utc)
    logger.info(f'Test duration: {ts_end - ts_start}')
    logger.info('############################################################')
    logger.info('###                 Parser test ran OK                   ###')
    logger.info('############################################################')


if __name__ == "__main__":
    main()
