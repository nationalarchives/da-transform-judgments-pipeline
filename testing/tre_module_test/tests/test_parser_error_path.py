import logging
from consignment_tester import ConsignmentTester
from test_consignment import TestConsignment
from datetime import datetime, timezone
from tests.tre_utils import send_tdr_bagit_message, validate_metadata_keys_common
from tests.tre_utils import create_test_output_dir, save_url_to_file
from tests.tre_utils import get_file_from_tar_as_json, get_file_from_tar_as_utf8
from tests.tre_utils import AWS_STEP_FUNCTION_STATUS_SUCCEEDED
from tests.tre_utils import KEY_CONSIGNMENT_REF
from tests.tre_utils import KEY_NUMBER_OF_RETRIES
from tests.tre_utils import KEY_CONSIGNMENT_TYPE
from tests.tre_utils import KEY_S3_FOLDER_URL

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)


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
    validate_metadata_keys_common(metadata=test_metadata_json, tc=tc, ct=ct)
    
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
