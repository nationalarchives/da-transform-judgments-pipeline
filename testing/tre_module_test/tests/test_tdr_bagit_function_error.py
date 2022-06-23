import logging
from consignment_tester import ConsignmentTester
from test_consignment import TestConsignment
from datetime import datetime, timezone
from tests.tre_utils import AWS_STEP_FUNCTION_STATUS_FAILED
from tests.tre_utils import ERR_MSG_UNEXPECTED_STATEMACHINE_VALUE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)

def test_tdr_bagit_function_error(ct: ConsignmentTester):
    """
    Test bagit function error path (by sending invalid input message).
    """
    logger.info('### test_tdr_bagit_function_error start ###################')
    test_start_datetime = datetime.now(tz=timezone.utc)
    cr = 'TEST-FUNC-ERR-PATH-BAGIT'
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



