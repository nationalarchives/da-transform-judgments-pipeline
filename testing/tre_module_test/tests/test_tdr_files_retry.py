import logging
from consignment_tester import ConsignmentTester
from test_consignment import TestConsignment
from tests.tre_utils import send_tdr_bagit_message
from tests.tre_utils import AWS_STEP_FUNCTION_STATUS_SUCCEEDED, AWS_STEP_FUNCTION_STATUS_FAILED
from tests.tre_utils import ERR_MSG_UNEXPECTED_STATEMACHINE_VALUE
from tests.tre_utils import ERR_MSG_DID_NOT_FIND_EXPECTED_TEXT
from tests.tre_utils import TEST_CHECKSUM_ERROR_TEXT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)


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
