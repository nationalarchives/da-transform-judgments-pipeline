import logging
from consignment_tester import ConsignmentTester
from test_consignment import TestConsignment
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)


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
