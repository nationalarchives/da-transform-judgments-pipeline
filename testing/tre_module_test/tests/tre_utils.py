import logging
import os
from consignment_tester import ConsignmentTester
from test_consignment import TestConsignment
from datetime import datetime, timezone
import requests
import os
import tarfile
import json

KEY_CONSIGNMENT = 's3_consignment'
KEY_S3_BUCKET = 's3_bucket'
KEY_S3_KEY_BAGIT = 's3_key_bagit'
KEY_S3_KEY_CHECKSUM = 's3_key_checksum'
KEY_S3_PRESIGNED_URL_EXPIRY = 'presigned_url_expiry_seconds'
KEY_CONSIGNMENT_REF = 'consignment-reference'
KEY_CONSIGNMENT_TYPE = 'consignment-type'
KEY_NUMBER_OF_RETRIES = 'number-of-retries'
KEY_S3_FOLDER_URL = 's3-folder-url'
KEY_LAMBDA_VERSIONS = 'lambda-functions-version'

AWS_STEP_FUNCTION_STATUS_RUNNING = 'RUNNING'
AWS_STEP_FUNCTION_STATUS_SUCCEEDED = 'SUCCEEDED'
AWS_STEP_FUNCTION_STATUS_FAILED = 'FAILED'
AWS_STEP_FUNCTION_STATUS_TIMED_OUT = 'TIMED_OUT'
AWS_STEP_FUNCTION_STATUS_ABORTED = 'ABORTED'

AWS_STEP_FUNCTION_STATUS_LIST = [
    AWS_STEP_FUNCTION_STATUS_RUNNING,
    AWS_STEP_FUNCTION_STATUS_SUCCEEDED,
    AWS_STEP_FUNCTION_STATUS_FAILED,
    AWS_STEP_FUNCTION_STATUS_TIMED_OUT,
    AWS_STEP_FUNCTION_STATUS_ABORTED
]

ERR_MSG_UNEXPECTED_STATEMACHINE_VALUE = 'Unexpected StateMachine value'
ERR_MSG_DID_NOT_FIND_EXPECTED_TEXT = 'Did not find expected error message text'
TEST_CHECKSUM_ERROR_TEXT = 'does not match expected checksum'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)


def create_test_output_dir(ts: datetime) -> str:
    path = f'test_outputs/pipeline_test_{ts.isoformat()}'
    if os.path.exists(path):
        raise ValueError(f'Test output path "{path}" already exists')    
    os.makedirs(path)
    return path


def save_url_to_file(url: str, output_file: str):
    logger.info(f'save_url_to_file: url={url} output_file={output_file}')
    with requests.get(url=url, stream=True) as r:
        r.raise_for_status()
        with open(output_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def get_file_from_tar_as_bytes(tar: str, file: str) -> bytes:
    with tarfile.open(tar, 'r') as t:
        return t.extractfile(file).read()


def get_file_from_tar_as_utf8(tar: str, file: str) -> str:
    return get_file_from_tar_as_bytes(tar=tar, file=file).decode('utf8')


def get_file_from_tar_as_json(tar: str, file: str) -> json:
    return json.loads(get_file_from_tar_as_utf8(tar=tar, file=file))


def validate_metadata_keys_common(metadata: dict, tc: TestConsignment, ct: ConsignmentTester):
    logger.info('validate_metadata_keys_common start')
    assert 'producer' in metadata, f'Key "producer" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert 'parameters' in metadata, f'Key "parameters" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert 'TRE' in metadata['parameters'], f'Key "TRE" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert 'PARSER' in metadata['parameters'], f'Key "PARSER" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert 'TDR' in metadata['parameters'], f'Key "TDR" key is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert f'TRE-{tc.consignment_ref}' in metadata['parameters']['TRE']['reference'], f'Key "TRE-{tc.consignment_ref}" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert KEY_LAMBDA_VERSIONS in metadata['parameters']['TRE'], f'Key "{KEY_LAMBDA_VERSIONS}" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert ct.environment.lambda_name_bagit_check in metadata['parameters']['TRE'][KEY_LAMBDA_VERSIONS], f'Key "{ct.environment.lambda_name_bagit_check}" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert ct.environment.lambda_name_files_check in metadata['parameters']['TRE'][KEY_LAMBDA_VERSIONS], f'Key "{ct.environment.lambda_name_files_check}" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert ct.environment.lambda_name_parser_input in metadata['parameters']['TRE'][KEY_LAMBDA_VERSIONS], f'Key "{ct.environment.lambda_name_parser_input}" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert ct.environment.lambda_name_parser in metadata['parameters']['TRE'][KEY_LAMBDA_VERSIONS], f'Key "{ct.environment.lambda_name_parser}" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert ct.environment.lambda_name_ed_int in metadata['parameters']['TRE'][KEY_LAMBDA_VERSIONS], f'Key "{ct.environment.lambda_name_ed_int}" is not in JSON metadata file "{tc.tar_metadata_file}"'
    assert ct.environment.lambda_name_slack_alerts in metadata['parameters']['TRE'][KEY_LAMBDA_VERSIONS], f'Key "{ct.environment.lambda_name_slack_alerts}" is not in JSON metadata file "{tc.tar_metadata_file}"'
    logger.info('validate_metadata_keys_common end')


def validate_metadata_keys(metadata: dict, tc:TestConsignment, ct: ConsignmentTester):
    logger.info('validate_metadata_keys start')
    validate_metadata_keys_common(metadata=metadata, tc=tc, ct=ct)
    assert metadata['parameters']['TRE']['payload']['log'] == 'parser.log', f'Did not find "parser.log" entry in JSON metadata file "{tc.tar_metadata_file}"'
    logger.info('validate_metadata_keys end')


def send_tdr_bagit_message(
        ct: ConsignmentTester,
        tc: TestConsignment,
        number_of_retries: int,
        expected_completion_status: str
) -> dict:
    """
    Submit a "TDR" input message to SQS with the specified `number_of_retries`
    (sends to queue "$(env)-tre-tdr-in)").
    """
    logger.info('send_tdr_bagit_message start')
    assert expected_completion_status in AWS_STEP_FUNCTION_STATUS_LIST, f'Requested status "{expected_completion_status}" not in {AWS_STEP_FUNCTION_STATUS_LIST}'

    # Note start time of run (to aid finding execution later)
    test_start_datetime = datetime.now(tz=timezone.utc)

    sqs_result = ct.send_tdr_sqs_message_consignment(tc=tc, number_of_retries=number_of_retries)
    logger.info(f'sqs_result={sqs_result}')

    executions = ct.get_step_function_executions(
        from_date=test_start_datetime,
        consignment_ref=tc.consignment_ref)

    logger.info(f'executions={executions}')

    if len(executions) == 0:
        raise ValueError(f'Failed to find step function execution for {tc.consignment_ref}')

    if executions[0]['status'] != expected_completion_status:
        raise ValueError('Failed execution for {tc.consignment_ref}; status '
                f'is {executions[0]["status"]} but required {expected_completion_status}')

    logger.info('send_tdr_bagit_message return')
    return executions[0]
