import logging
from consignment_tester import ConsignmentTester
from test_consignment import TestConsignment
from datetime import datetime, timezone
from tests.tre_utils import create_test_output_dir
from tests.tre_utils import save_url_to_file
from tests.tre_utils import get_file_from_tar_as_json
from tests.tre_utils import validate_metadata_keys_common

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)


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
    validate_metadata_keys_common(metadata=test1_metadata_json, tc=tc)
    assert test1_metadata_json['parameters']['TRE']['payload']['log'] == 'parser.log', f'Did not find "parser.log" entry in JSON metadata file {tc.tar_metadata_file}'
    logger.info('test_ok_path completed OK')

