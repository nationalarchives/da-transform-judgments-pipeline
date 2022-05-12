import logging
import boto3
import os
from environment import Environment
from test_consignment import TestConsignment
from datetime import datetime
import time
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)


class ConsignmentTester():
    ENV_AWS_PROFILE = 'AWS_PROFILE'

    """SQS -> Step Function : Check S3 Result"""
    def __init__(self, s3_data_bucket, environment: Environment,
            aws_profile_data=None, aws_profile_env=None):

        self.s3_data_bucket = s3_data_bucket
        self.environment = environment

        logger.info(f'ConsignmentTester __init__ : '
            f's3_data_bucket={s3_data_bucket} '
            f'aws_profile_data={aws_profile_data} '
            f'aws_profile_env={aws_profile_env}')

        # Fallback to AWS_PROFILE env var if no AWS profile(s) specified
        if (aws_profile_data is None) or (len(aws_profile_data) == 0):
            if (
              (self.ENV_AWS_PROFILE in os.environ) and 
              (len(os.environ[self.ENV_AWS_PROFILE]) > 0)
            ):
                aws_profile_data = os.environ[self.ENV_AWS_PROFILE]
            else:
                raise ValueError('No AWS environment(s) specified or set in '
                    f'{self.ENV_AWS_PROFILE}')

        self.aws_session_data = boto3.Session(profile_name=aws_profile_data)
        if aws_profile_env is None:
            logger.info('Using same AWS_PROFILE for data and env')
            self.aws_session_env = self.aws_session_data
        else:
            self.aws_session_env = boto3.Session(profile_name=aws_profile_env) 

        logger.info(f'aws_profile_data={aws_profile_data} aws_profile_env={aws_profile_env}')
        self.aws_client_data_s3 = self.aws_session_data.client('s3')
        self.aws_client_env_s3 = self.aws_session_env.client('s3')
        self.aws_resource_env_s3 = self.aws_session_env.resource('s3')
        self.aws_client_env_sqs = self.aws_session_env.client('sqs')
        self.aws_client_env_sf = self.aws_session_env.client('stepfunctions')


    def send_sqs_message(
            self,
            sqs_message: str,
            sqs_url: str
    ) -> str:
        logger.info(f'send_sqs_message: sqs_url={sqs_url} sqs_message={sqs_message}')

        # SQS send to tre-tdr-in
        sqs_response = self.aws_client_env_sqs.send_message(
            QueueUrl=sqs_url,
            MessageBody=sqs_message
        )

        logger.info(f'sqs_response={sqs_response}')

        if sqs_response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise ValueError('Send to tre-tdr-in did not return '
                f'HTTPStatusCode 200; response was: {sqs_response}')

        return sqs_response


    def send_sqs_message_tdr(
            self,
            sqs_message: str
    ) -> str:
        logger.info(f'send_sqs_message_tdr: {sqs_message}')
        logger.info(f'self.environment.sqs_tre_tdr_in_url: {self.environment.sqs_tre_tdr_in_url}')
        
        # SQS send to tre-tdr-in
        return self.send_sqs_message(
                sqs_message=sqs_message,
                sqs_url=self.environment.sqs_tre_tdr_in_url)


    def send_sqs_message_editorial_retry(
            self,
            sqs_message: str
    ) -> str:
        logger.info(f'send_sqs_message_editorial_retry: {sqs_message}')
        logger.info(f'self.environment.sqs_tre_tdr_in_url: {self.environment.sqs_tre_tdr_in_url}')

        # SQS send to tre-editorial-retry
        return self.send_sqs_message(
                sqs_message=sqs_message,
                sqs_url=self.environment.sqs_tre_editorial_retry)


    def send_tdr_sqs_message_consignment(
            self,
            tc: TestConsignment,
            number_of_retries: int,
            presigned_url_expiry_seconds: int=60,
            extra_data: str=''
    ):
        """
        Submit a test consignment in S3 to the Judgment Step Function and
        check for the expected result.

        Use `extra_data` to stop SQS message de-duplication if testing sending
        duplicate messages (e.g. insert whitespace such as ' ' or some valid
        JSON value such as ',"foo": "bar"').
        """
        url_bagit = '' if not tc.s3_key_bagit else self.aws_client_data_s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.s3_data_bucket, 'Key': tc.s3_key_bagit},
            ExpiresIn=presigned_url_expiry_seconds)

        url_checksum = '' if not tc.s3_key_checksum else self.aws_client_data_s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.s3_data_bucket, 'Key': tc.s3_key_checksum},
            ExpiresIn=presigned_url_expiry_seconds)

        sqs_message = (
            '{\n'
            f'    "consignment-reference": "{tc.consignment_ref}",\n'
            f'    "s3-bagit-url": "{url_bagit}",\n'
            f'    "s3-sha-url": "{url_checksum}",\n'
            f'    "consignment-type": "judgment",\n'
            f'    "number-of-retries": {number_of_retries}\n'
            f'{extra_data}'
            '}\n'
        )

        return self.send_sqs_message_tdr(sqs_message=sqs_message)


    def get_step_function_executions(
            self,
            from_date: datetime,
            consignment_ref: str,
            target_status: list=['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED'],
            max_reties: int=180,
            wait_secs: int=1,
            stop_poll_when_more_than: int=0
    ):
        """
        target_status: 'RUNNING'|'SUCCEEDED'|'FAILED'|'TIMED_OUT'|'ABORTED'
        """
        # Poll for the specified Step Function execution
        found = False  
        retry = 0
        filtered_result = []

        while not found and retry < max_reties:
            retry += 1
            logger.info(f'get_step_function_executions: from_date={from_date} '
                    f'consignment_ref={consignment_ref}')

            # Can only filter by status here; filter by prefix after call
            result = self.aws_client_env_sf.list_executions(
                stateMachineArn=self.environment.step_function_tre_state_machine_arn)
            
            # Filter by name, time and multiple status values; boto3 API can't
            filtered_result = [
                e for e in result['executions']
                if (
                    e['name'].startswith(f'tre-{consignment_ref}') and
                    (e['startDate'] >= from_date) and
                    (e['status'] in target_status)
                )
            ]

            logger.info(f'get_step_function_executions: unfiltered '
                f'len(result["executions"])={len(result["executions"])} '
                f'len(filtered_result)={len(filtered_result)}')

            found = (len(filtered_result) > stop_poll_when_more_than)
            
            if not found and retry < max_reties:
                logger.info(f'get_step_function_executions: '
                        f'retry={retry}/{max_reties} wait_secs={wait_secs}')
                time.sleep(wait_secs)
            
            if found:
                return filtered_result

        raise ValueError('Timed out waiting for response; '
                f'from_date={from_date} '
                f'consignment_ref={consignment_ref} '
                f'target_status={target_status} '
                f'max_reties={max_reties} '
                f'wait_secs={wait_secs} '
                f'stop_poll_when_more_than={stop_poll_when_more_than}')


    def get_step_function_step_result(
            self,
            arn: str,
            step_name: str
    ) -> dict:
        """
        Get the specified Step Function execution `arn` and return the input
        and output payloads for `step_name` in the form:

        {
            'input': ... ,
            'output': ...
        }
        """
        KEY_STATE_ENTERED = 'stateEnteredEventDetails'
        KEY_STATE_EXITED = 'stateExitedEventDetails'
        KEY_INPUT = 'input'
        KEY_OUTPUT = 'output'

        sf_history = self.aws_client_env_sf.get_execution_history(executionArn=arn)
        logger.debug(f'sf_history={sf_history}')

        step_input = [
            json.loads(e[KEY_STATE_ENTERED][KEY_INPUT])
            for e in sf_history['events']
            if (
                (KEY_STATE_ENTERED in e) and
                ('name' in e[KEY_STATE_ENTERED]) and
                (str(e[KEY_STATE_ENTERED]['name']) == step_name)
            )
        ]

        step_output = [
            json.loads(e[KEY_STATE_EXITED][KEY_OUTPUT])
            for e in sf_history['events']
            if (
                (KEY_STATE_EXITED in e) and
                ('name' in e[KEY_STATE_EXITED]) and
                (str(e[KEY_STATE_EXITED]['name']) == step_name)
            )
        ]

        if len(step_input) != 1:
            raise ValueError(f'Expected to find 1 input for step '
                    f'"{step_name}" but found {len(step_input)}')

        if len(step_output) != 1:
            raise ValueError(f'Expected to find 1 output for step '
                    f'"{step_name}" but found {len(step_output)}')

        return {
            KEY_INPUT: step_input[0],
            KEY_OUTPUT: step_output[0]
        }


    def delete_from_s3(self, s3_bucket, s3_prefix: str):
        logger.info(f'delete_from_s3: s3_bucket={s3_bucket} s3_prefix={s3_prefix}')
        objects = s3_bucket.objects.filter(Prefix=s3_prefix)
        logger.info(f'delete_from_s3: s3_bucket={s3_bucket} objects={[o.key for o in objects]}')
        objects.delete()
    

    def delete_from_s3_tre_temp(
            self,
            consignment_ref: str,
            prefix: str='consignments/judgment/',
            suffix: str='/'
    ):
        logger.info(f'delete_from_s3_tre_temp: consignment_ref={consignment_ref}')
        self.delete_from_s3(
            s3_bucket=self.aws_resource_env_s3.Bucket(self.environment.s3_bucket_tre_temp),
            s3_prefix=f'{prefix}{consignment_ref}{suffix}')
    
    def delete_from_s3_tre_editorial_judgment_out(
            self,
            consignment_ref: str,
            prefix: str='parsed/judgment/',
            suffix: str='/'
    ):
        logger.info(f'delete_from_s3_tre_editorial_judgment_out: consignment_ref={consignment_ref}')
        self.delete_from_s3(
            s3_bucket=self.aws_resource_env_s3.Bucket(self.environment.s3_bucket_tre_editorial_judgment_out),
            s3_prefix=f'{prefix}{consignment_ref}{suffix}')
