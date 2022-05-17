import logging
import boto3
import os
import sys
import json
from datetime import datetime, timezone
import requests
import tarfile
from enum import Enum
from test_consignment import TestConsignment
from consignment_tester import ConsignmentTester
from environment import Environment

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)

KEY_CONSIGNMENT = 's3_consignment'
KEY_S3_BUCKET = 's3_bucket'
KEY_S3_KEY_BAGIT = 's3_key_bagit'
KEY_S3_KEY_CHECKSUM = 's3_key_checksum'
KEY_S3_PRESIGNED_URL_EXPIRY = 'presigned_url_expiry_seconds'
KEY_CONSIGNMENT_REF = 'consignment-reference'
KEY_CONSIGNMENT_TYPE = 'consignment-type'
KEY_NUMBER_OF_RETRIES = 'number-of-retries'
KEY_S3_FOLDER_URL = 's3-folder-url'

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

TEST_CHECKSUM_ERROR_TEXT = 'does not match expected checksum'
ERR_MSG_DID_NOT_FIND_EXPECTED_TEXT = 'Did not find expected error message text'
ERR_MSG_UNEXPECTED_STATEMACHINE_VALUE = 'Unexpected StateMachine value'

s3c = boto3.client('s3')


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

def validate_metadata_json_file(metadata_json: dict, tc:TestConsignment):
    assert 'producer' in metadata_json, f'Key "producer" is not in JSON metadata file {tc.tar_metadata_file}'
    assert 'parameters' in metadata_json, f'Key "parameters" is not in JSON metadata file {tc.tar_metadata_file}'
    assert 'TRE' in metadata_json['parameters'], f'Key "TRE" is not in JSON metadata file {tc.tar_metadata_file}'
    assert 'PARSER' in metadata_json['parameters'], f'Key "PARSER" is not in JSON metadata file {tc.tar_metadata_file}'
    assert 'TDR' in metadata_json['parameters'], f'Key "TDR" key is not in JSON metadata file {tc.tar_metadata_file}'
    assert f'TRE-{tc.consignment_ref}' in metadata_json['parameters']['TRE']['reference'], f'Key "TRE-{tc.consignment_ref}" key is not in JSON metadata file {tc.tar_metadata_file}'
    assert metadata_json['parameters']['TRE']['payload']['log'] == 'parser.log', f'Did not find "parser.log" entry in JSON metadata file {tc.tar_metadata_file}'


def validate_metadata(metadata: dict, tc: TestConsignment):
    assert 'producer' in metadata, f'Key "producer" is not in JSON metadata file {tc.tar_metadata_file}'
    assert 'parameters' in metadata, f'Key "parameters" is not in JSON metadata file {tc.tar_metadata_file}'
    assert 'TRE' in metadata['parameters'], f'Key "TRE" is not in JSON metadata file {tc.tar_metadata_file}'
    assert 'PARSER' in metadata['parameters'], f'Key "PARSER" is not in JSON metadata file {tc.tar_metadata_file}'
    assert 'TDR' in metadata['parameters'], f'Key "TDR" key is not in JSON metadata file {tc.tar_metadata_file}'
    assert f'TRE-{tc.consignment_ref}' in metadata['parameters']['TRE']['reference'], f'Key "TRE-{tc.consignment_ref}" key is not in JSON metadata file {tc.tar_metadata_file}'


def test_ok_path(ct: ConsignmentTester, tc: TestConsignment):
    """
    Submit a valid test consignment and verify the output tar.gz file.
    """
    ct.delete_from_s3_tre_temp(consignment_ref=tc.consignment_ref)
    ct.delete_from_s3_tre_editorial_judgment_out(consignment_ref=tc.consignment_ref)

    # Note start time of run (to aid finding execution later)
    test_start_datetime = datetime.now(tz=timezone.utc)

    sqs_result = ct.send_tdr_sqs_message_consignment(tc=tc, number_of_retries=0)
    logger.info(f'sqs_result={sqs_result}')

    executions = ct.get_step_function_executions(
        from_date=test_start_datetime,
        consignment_ref=tc.consignment_ref)

    logger.info(f'executions={executions}')

    if len(executions) == 0:
        raise ValueError(f'Failed to find step function execution for {tc.consignment_ref}')

    if executions[0]['status'] != 'SUCCEEDED':
        raise ValueError('Failed execution for {tc.consignment_ref}; status '
                f'is {executions[0]["status"]} but required SUCCEEDED')

    step_result = ct.get_step_function_step_result(
          arn=executions[0]['executionArn'],
          step_name='EditorialIntegration')

    logger.info(f'type(step_result)={type(step_result)}')
    logger.info(f'step_result={step_result}')
    editorial_presigned_url = step_result['output']['editorial-output']['s3-folder-url']
    test_output_dir = create_test_output_dir(test_start_datetime)
    test1_tar_gz = f'{test_output_dir}/test1.tar.gz'
    save_url_to_file(url=editorial_presigned_url, output_file=test1_tar_gz)
    test1_metadata_json = get_file_from_tar_as_json(tar=test1_tar_gz, file=tc.tar_metadata_file)
    logger.info(f'test1_metadata_json={test1_metadata_json}')
    validate_metadata(metadata=test1_metadata_json, tc=tc)
    assert test1_metadata_json['parameters']['TRE']['payload']['log'] == 'parser.log', f'Did not find "parser.log" entry in JSON metadata file {tc.tar_metadata_file}'
    logger.info('test_ok_path completed OK')


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


def verify_tdr_bagit_retry_ok_path(
        ct: ConsignmentTester,
        execution: dict,
        output_message_retry_number: int
):
    """
    Helper function for test_tdr_bagit_retry to check success path.
    """
    logger.info('verify_tdr_bagit_retry_ok_path start')
    step_result = ct.get_step_function_step_result(
          arn=execution['executionArn'],
          step_name='TDR BagIt Error Slack Alerts')

    logger.info(f'type(step_result)={type(step_result)}')
    logger.info(f'step_result={step_result}')

    assert step_result['input']['error'] == True, 'Expected error key to be true, but it was not'
    assert TEST_CHECKSUM_ERROR_TEXT in step_result['input']['error-message'], ERR_MSG_DID_NOT_FIND_EXPECTED_TEXT
    assert step_result['input']['output-message']['number-of-retries'] == output_message_retry_number, 'Did not find number-of-retries = 1 in output message'
    logger.info('verify_tdr_bagit_retry_ok_path end')


def verify_tdr_bagit_retry_fail_path(
        ct: ConsignmentTester,
        execution: dict
):
    """
    Helper function for test_tdr_bagit_retry to check failure path.
    """
    logger.info('verify_tdr_bagit_retry_fail_path start')
    step_result = ct.get_step_function_step_result(
          arn=execution['executionArn'],
          step_name='Bagit Checksum Error Slack Alerts')

    logger.info(f'type(step_result)={type(step_result)}')
    logger.info(f'step_result={step_result}')

    assert step_result['input']['ErrorType'] == 'Bagit Checksum Error', 'Unexpected ErrorType value'
    assert step_result['input']['StateMachine'] == f'{ct.environment.step_function_name}', ERR_MSG_UNEXPECTED_STATEMACHINE_VALUE
    assert TEST_CHECKSUM_ERROR_TEXT in step_result['input']['ErrorMessage'], ERR_MSG_DID_NOT_FIND_EXPECTED_TEXT
    logger.info('verify_tdr_bagit_retry_fail_path end')


def test_tdr_bagit_retry(ct: ConsignmentTester, tc: TestConsignment):
    """
    Send retries and verify stops at fail state at limit (currently < 3). Uses
    invalid bagit checksum to trigger retry path.
    """
    logger.info('### test_tdr_bagit_retry start ############################')
    ct.delete_from_s3_tre_temp(consignment_ref=tc.consignment_ref)
    ct.delete_from_s3_tre_editorial_judgment_out(consignment_ref=tc.consignment_ref)

    execution = send_tdr_bagit_message(ct=ct, tc=tc, number_of_retries=0, expected_completion_status=AWS_STEP_FUNCTION_STATUS_SUCCEEDED)
    verify_tdr_bagit_retry_ok_path(ct=ct, execution=execution, output_message_retry_number=1)
    execution = send_tdr_bagit_message(ct=ct, tc=tc, number_of_retries=1, expected_completion_status=AWS_STEP_FUNCTION_STATUS_SUCCEEDED)
    verify_tdr_bagit_retry_ok_path(ct=ct, execution=execution, output_message_retry_number=2)
    execution = send_tdr_bagit_message(ct=ct, tc=tc, number_of_retries=2, expected_completion_status=AWS_STEP_FUNCTION_STATUS_FAILED)
    verify_tdr_bagit_retry_fail_path(ct=ct, execution=execution)
    logger.info('test_tdr_bagit_retry completed OK')


def test_tdr_bagit_function_error(ct: ConsignmentTester):
    """
    Test bagit function error path (by sending invalid input message).
    """
    logger.info('### test_tdr_bagit_function_error start ###################')
    test_start_datetime = datetime.now(tz=timezone.utc)
    cr = 'TEST-FUNCTION-ERROR-PATH-BAGIT'
    sqs_result = ct.send_sqs_message_tdr(sqs_message=f'{{"consignment-reference": "{cr}"}}')
    logger.info(f'sqs_result={sqs_result}')
    executions = ct.get_step_function_executions(
        from_date=test_start_datetime,
        consignment_ref=cr)

    logger.info(f'executions={executions}')
    assert len(executions) != 0, 'Failed to find step function execution for bagit function error test'

    if executions[0]['status'] != AWS_STEP_FUNCTION_STATUS_FAILED:
        raise ValueError(f'Step Function bagit error test failed; status is '
                f'{executions[0]["status"]} but required {AWS_STEP_FUNCTION_STATUS_FAILED}')

    step_result = ct.get_step_function_step_result(
        arn=executions[0]['executionArn'],
        step_name='Bagit Checksum Error Slack Alerts'
    )

    logger.info(f'step_result={step_result}')
    assert step_result['input']['Execution'].startswith(f'tre-{cr}'), 'Invalid Execution key value'
    assert step_result['input']['ErrorType'] == 'Bagit Checksum Function Error', 'Invalid ErrorType'
    assert step_result['input']['StateMachine'] == f'{ct.environment.step_function_name}', ERR_MSG_UNEXPECTED_STATEMACHINE_VALUE
    assert 'ErrorMessage' in step_result['input'], 'Missing ErrorMessage'
    logger.info('test_tdr_bagit_function_error completed OK')



def verify_tdr_files_retry_ok_path(
        ct: ConsignmentTester,
        execution: dict,
        output_message_retry_number: int
):
    """
    Helper function for test_tdr_files_retry to check success path.
    """
    logger.info('verify_tdr_files_retry_ok_path start')
    step_result = ct.get_step_function_step_result(
          arn=execution['executionArn'],
          step_name='TDR Files Error Slack Alerts')

    logger.info(f'type(step_result)={type(step_result)}')
    logger.info(f'step_result={step_result}')

    assert step_result['input']['error'] == True, 'Expected error key to be true, but it was not'
    assert TEST_CHECKSUM_ERROR_TEXT in step_result['input']['error-message'], ERR_MSG_DID_NOT_FIND_EXPECTED_TEXT
    assert step_result['input']['output-message']['number-of-retries'] == output_message_retry_number, 'Did not find number-of-retries = 1 in output message'
    logger.info('verify_tdr_files_retry_ok_path end')


def verify_tdr_files_retry_fail_path(
        ct: ConsignmentTester,
        execution: dict
):
    """
    Helper function for test_tdr_bagit_retry to check failure path.
    """
    logger.info('verify_tdr_files_retry_fail_path start')
    step_result = ct.get_step_function_step_result(
          arn=execution['executionArn'],
          step_name='File Checksum Error Slack Alerts')

    logger.info(f'type(step_result)={type(step_result)}')
    logger.info(f'step_result={step_result}')

    assert 'Execution' in step_result['input'], 'Missing key "Execution"'
    assert step_result['input']['ErrorType'] == 'Files Checksum Error', 'Unexpected ErrorType value'
    assert step_result['input']['StateMachine'] == f'{ct.environment.step_function_name}', ERR_MSG_UNEXPECTED_STATEMACHINE_VALUE
    assert 'does not match expected checksum' in step_result['input']['ErrorMessage'], ERR_MSG_DID_NOT_FIND_EXPECTED_TEXT
    logger.info('verify_tdr_files_retry_fail_path end')


def test_tdr_files_retry(ct: ConsignmentTester, tc: TestConsignment):
    """
    Send retries and verify stops at fail state at limit (currently < 3).
    """
    logger.info('### test_tdr_files_retry start ############################')
    ct.delete_from_s3_tre_temp(consignment_ref=tc.consignment_ref)
    ct.delete_from_s3_tre_editorial_judgment_out(consignment_ref=tc.consignment_ref)

    execution = send_tdr_bagit_message(ct=ct, tc=tc, number_of_retries=0, expected_completion_status=AWS_STEP_FUNCTION_STATUS_SUCCEEDED)
    verify_tdr_files_retry_ok_path(ct=ct, execution=execution, output_message_retry_number=1)
    execution = send_tdr_bagit_message(ct=ct, tc=tc, number_of_retries=1, expected_completion_status=AWS_STEP_FUNCTION_STATUS_SUCCEEDED)
    verify_tdr_files_retry_ok_path(ct=ct, execution=execution, output_message_retry_number=2)
    execution = send_tdr_bagit_message(ct=ct, tc=tc, number_of_retries=2, expected_completion_status=AWS_STEP_FUNCTION_STATUS_FAILED)
    verify_tdr_files_retry_fail_path(ct=ct, execution=execution)
    logger.info('test_tdr_files_retry completed OK')


def test_parser_error_path(ct: ConsignmentTester, tc: TestConsignment):
    """
    Verify parser failure path (uses invalid .docx file)
    """
    logger.info('### test_parser_error_path start ##########################')
    test_start_datetime = datetime.now(tz=timezone.utc)
    ct.delete_from_s3_tre_temp(consignment_ref=tc.consignment_ref)
    ct.delete_from_s3_tre_editorial_judgment_out(consignment_ref=tc.consignment_ref)

    execution = send_tdr_bagit_message(ct=ct, tc=tc, number_of_retries=0, expected_completion_status=AWS_STEP_FUNCTION_STATUS_SUCCEEDED)

    step_result = ct.get_step_function_step_result(
        arn=execution['executionArn'],
        step_name='Editorial SNS Publish')

    logger.info(f'type(step_result)={type(step_result)}')
    logger.info(f'step_result={step_result}')

    KEY_ED_OUTPUT = 'editorial-output'
    assert step_result['input'][KEY_ED_OUTPUT][KEY_CONSIGNMENT_REF] == tc.consignment_ref, 'Failed to find consignment reference in output'
    assert step_result['input'][KEY_ED_OUTPUT][KEY_NUMBER_OF_RETRIES] == 0, 'Did not find expected number of retries in output'
    assert step_result['input'][KEY_ED_OUTPUT][KEY_CONSIGNMENT_TYPE] == 'judgment', 'Did not find expected consignment type in output'
    s3_folder_url = step_result['input'][KEY_ED_OUTPUT][KEY_S3_FOLDER_URL]

    test_output_dir = create_test_output_dir(test_start_datetime)
    test_tar_gz = f'{test_output_dir}/test_parser_error_path.tar.gz'
    save_url_to_file(url=s3_folder_url, output_file=test_tar_gz)
    test_metadata_json = get_file_from_tar_as_json(tar=test_tar_gz, file=tc.tar_metadata_file)
    logger.info(f'test_metadata_json={test_metadata_json}')
    validate_metadata(metadata=test_metadata_json, tc=tc)
    
    tar_file = (
            tc.consignment_ref + '/' +
            test_metadata_json['parameters']['TRE']['payload']['filename'])
    
    bad_docx_text = get_file_from_tar_as_utf8(
          tar=test_tar_gz,
          file=tar_file)
    
    logger.info(f'bad_docx_text={bad_docx_text}')

    assert bad_docx_text == 'This is an intentionally invalid docx file for testing purposes', 'Failed to find expected text in intentionally bad docx file'
    assert type(test_metadata_json['parameters']['PARSER']['error-messages']) is list, 'PARSER error-messages record is not a list'
    assert len(test_metadata_json['parameters']['PARSER']['error-messages']) > 0, 'PARSER error-messages record length is 0'
    logger.info('test_parser_error_path completed OK')


def send_editorial_retry_message(
        ct: ConsignmentTester,
        tc:TestConsignment,
        number_of_retries: int,
        expected_completion_status: str
):
    """
    Submit a "TDR" input message to SQS with the specified `number_of_retries`
    (sends to queue "$(env)-tre-editorial-retry)").
    """
    logger.info('send_editorial_retry_message start')
    assert expected_completion_status in AWS_STEP_FUNCTION_STATUS_LIST, f'Requested status "{expected_completion_status}" not in {AWS_STEP_FUNCTION_STATUS_LIST}'
    test_start_datetime = datetime.now(tz=timezone.utc)
    sqs_message = (
        '{\n'
        f'    "consignment-reference": "{tc.consignment_ref}",\n'
        f'    "consignment-type": "judgment",\n'
        f'    "number-of-retries": {number_of_retries}\n'
        '}\n'
    )

    sqs_result = ct.send_sqs_message_editorial_retry(sqs_message=sqs_message)
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

    logger.info('send_editorial_retry_message return')
    return executions[0]


def verify_editorial_retry_ok_path(
        ct: ConsignmentTester,
        tc: TestConsignment,
        execution: dict,
        expected_number_of_retries: int
):
    """
    Helper function for test_tdr_bagit_retry to check success path.
    """
    logger.info('verify_editorial_retry_ok_path start')
    step_result = ct.get_step_function_step_result(
          arn=execution['executionArn'],
          step_name='Editorial SNS Publish')

    logger.info(f'type(step_result)={type(step_result)}')
    logger.info(f'step_result={step_result}')

    assert step_result['input']['editorial-output']['consignment-reference'] == tc.consignment_ref, 'Invalid consignment-reference'
    assert step_result['input']['editorial-output']['consignment-type'] == 'judgment', 'Invalid consignment-type'
    assert step_result['input']['editorial-output']['number-of-retries'] == expected_number_of_retries, 'Invalid number-of-retries'
    presigned_url = step_result['input']['editorial-output']['s3-folder-url']
    dtm = datetime.now(tz=timezone.utc)
    test_output_dir = create_test_output_dir(dtm)
    tgz = f'{test_output_dir}/test.tar.gz'
    save_url_to_file(url=presigned_url, output_file=tgz)
    metadata_json = get_file_from_tar_as_json(tar=tgz, file=tc.tar_metadata_file)
    logger.info(f'metadata_json={metadata_json}')
    validate_metadata_json_file(metadata_json=metadata_json, tc=tc)
    logger.info('verify_editorial_retry_ok_path end')


def verify_editorial_retry_limit_exceeded_path(
        ct: ConsignmentTester,
        tc: TestConsignment,
        execution: dict,
        expected_number_of_retries: int
):
    """
    Helper function for test_tdr_bagit_retry to check success path.
    """
    logger.info('verify_editorial_retry_ok_path start')
    step_result = ct.get_step_function_step_result(
          arn=execution['executionArn'],
          step_name='Exceeded Editorial Retry Limit Check Slack Alerts')

    logger.info(f'type(step_result)={type(step_result)}')
    logger.info(f'step_result={step_result}')

    assert step_result['input']['consignment-reference'] == tc.consignment_ref, 'Invalid consignment-reference'
    assert step_result['input']['consignment-type'] == 'judgment', 'Invalid consignment-type'
    assert step_result['input']['number-of-retries'] == expected_number_of_retries, 'Invalid number-of-retries'
    logger.info('verify_editorial_retry_ok_path end')


def test_editorial_retry(ct: ConsignmentTester, tc: TestConsignment):
    """
    Test editorial retry path.
    """
    logger.info('### test_editorial_retry start ############################')

    # Start with OK path test and re-use consignment for retries
    test_ok_path(ct=ct, tc=tc)

    execution = send_editorial_retry_message(ct=ct, tc=tc, number_of_retries=1, expected_completion_status=AWS_STEP_FUNCTION_STATUS_SUCCEEDED)
    verify_editorial_retry_ok_path(ct=ct, tc=tc, execution=execution, expected_number_of_retries=1)
    execution = send_editorial_retry_message(ct=ct, tc=tc, number_of_retries=2, expected_completion_status=AWS_STEP_FUNCTION_STATUS_SUCCEEDED)
    verify_editorial_retry_ok_path(ct=ct, tc=tc, execution=execution, expected_number_of_retries=2)
    execution = send_editorial_retry_message(ct=ct, tc=tc, number_of_retries=3, expected_completion_status=AWS_STEP_FUNCTION_STATUS_SUCCEEDED)
    verify_editorial_retry_ok_path(ct=ct, tc=tc, execution=execution, expected_number_of_retries=3)
    execution = send_editorial_retry_message(ct=ct, tc=tc, number_of_retries=4, expected_completion_status=AWS_STEP_FUNCTION_STATUS_SUCCEEDED)
    verify_editorial_retry_ok_path(ct=ct, tc=tc, execution=execution, expected_number_of_retries=4)
    execution = send_editorial_retry_message(ct=ct, tc=tc, number_of_retries=5, expected_completion_status=AWS_STEP_FUNCTION_STATUS_FAILED)
    verify_editorial_retry_limit_exceeded_path(ct=ct, tc=tc, execution=execution, expected_number_of_retries=5)

    logger.info('test_editorial_retry completed OK')


def test_tdr_duplicate_resend_parallel(ct: ConsignmentTester, tc: TestConsignment):
    logger.info('test_tdr_duplicate_resend_parallel')

    ct.delete_from_s3_tre_temp(consignment_ref=tc.consignment_ref)
    ct.delete_from_s3_tre_editorial_judgment_out(consignment_ref=tc.consignment_ref)

    # Note start time of run (to aid finding execution later)
    test_start_datetime = datetime.now(tz=timezone.utc)

    # Send number-of-retries=0, twice; extra_data to avoid SQS de-duplication
    sqs_result_1 = ct.send_tdr_sqs_message_consignment(tc=tc, number_of_retries=0, extra_data=' ')
    sqs_result_2 = ct.send_tdr_sqs_message_consignment(tc=tc, number_of_retries=0, extra_data='  ')
    logger.info(f'sqs_result_1={sqs_result_1}')
    logger.info(f'sqs_result_2={sqs_result_2}')

    executions = ct.get_step_function_executions(
        from_date=test_start_datetime,
        consignment_ref=tc.consignment_ref,
        stop_poll_when_more_than=1)

    logger.info(f'executions={executions}')

    if len(executions) == 0:
        raise ValueError(f'Failed to find step function execution for {tc.consignment_ref}')

    raise ValueError('TODO: Add checks to verify 2 the function executions are correct')

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

    test_tdr_bagit_retry(ct=ct, tc=tc_bagit_retry)
    test_tdr_bagit_function_error(ct=ct)  # no tc param; uses malformed message to deliberately fail
    test_tdr_files_retry(ct=ct, tc=tc_files_retry)
    test_parser_error_path(ct=ct, tc=tc_parser_error)
    test_editorial_retry(ct=ct, tc=tc_shared_consignment)
    # test_tdr_duplicate_resend_parallel(ct=ct, tc=tc_shared_consignment)
    logger.info('### All tests completed OK ################################')


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
