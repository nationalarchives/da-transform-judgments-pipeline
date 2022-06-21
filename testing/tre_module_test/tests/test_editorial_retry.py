import logging
from consignment_tester import ConsignmentTester
from test_consignment import TestConsignment
from datetime import datetime, timezone
from tests.tre_utils import create_test_output_dir, save_url_to_file, get_file_from_tar_as_json
from tests.tre_utils import validate_metadata_keys
from tests.tre_utils import AWS_STEP_FUNCTION_STATUS_LIST
from tests.tre_utils import AWS_STEP_FUNCTION_STATUS_SUCCEEDED, AWS_STEP_FUNCTION_STATUS_FAILED
from tests.test_ok_path import test_ok_path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)


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
    validate_metadata_keys(metadata=metadata_json, tc=tc, ct=ct)
    logger.info('verify_editorial_retry_ok_path end')


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

