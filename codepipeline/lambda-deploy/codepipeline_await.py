#!/usr/bin/env python3
import argparse
import logging
import os
import boto3
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)


class AWSSession():
    AWS_PROFILE = 'AWS_PROFILE'

    def __init__(self, aws_profile: str = None):
        logger.info(f'AWSSession __init__ : aws_profile={aws_profile}')

        # Fallback to AWS_PROFILE env var if no AWS profile(s) specified
        if (aws_profile is None) or (len(aws_profile) == 0):
            if (
                (self.AWS_PROFILE in os.environ)
                and
                (len(os.environ[self.AWS_PROFILE]) > 0)
            ):
                aws_profile = os.environ[self.AWS_PROFILE]
            else:
                raise ValueError('AWS profile not specified')

        self.session = boto3.Session(profile_name=aws_profile)
        self.codepipeline = self.session.client('codepipeline')

    def get_pipeline_execution(self, name: str, execution_id: str) -> dict:
        logger.info(f'get_pipeline_execution: name={name} '
                    f'execution_id={execution_id}')

        response = self.codepipeline.get_pipeline_execution(
            pipelineName=name,
            pipelineExecutionId=execution_id)

        logger.info(f'response={response}')
        return response


def await_codepipeline(
    name: str,
    execution_id: str,
    wait_seconds: int,
    attempt_count: int,
    aws_profile: str = None
):
    """
    Codepipeline status will be one of: Cancelled, InProgress, Stopped,
    Stopping, Succeeded, Superseded, Failed.
    """
    SUCCEEDED = 'Succeeded'
    IN_PROGRESS = 'InProgress'

    logger.info(f'await_codepipeline: name={name} '
                f' execution_id={execution_id} wait_seconds={wait_seconds} '
                f' attempt_count={attempt_count} aws_profile={aws_profile}')

    if attempt_count < 1:
        raise ValueError(f'attempt_count must be at least 1')

    aws = AWSSession(aws_profile=aws_profile)
    attempt = 1
    while attempt <= attempt_count:
        if attempt > 1:
            logger.info(f'Waiting {wait_seconds}s')
            time.sleep(wait_seconds)

        logger.info(f'Checking status, attempt ({attempt}/{attempt_count})')
        result = aws.get_pipeline_execution(
            name=name,
            execution_id=execution_id)

        logger.info(f'result={result}')

        status = str(result['pipelineExecution']['status'])
        logger.info(f'status={status}')

        if status.lower() == SUCCEEDED.lower():
            logger.info('Pipeline completed successfully')
            return
        elif status.lower() == IN_PROGRESS.lower():
            logger.info('Pipeline is still running')
        else:
            raise ValueError(f'Unexpected codepipeline status "{status}"')

        attempt += 1

    raise ValueError(f'Timeout waiting for execution ID "{execution_id}" '
                     f'in codepipeline "{name}"')


# Parse CLI arguments and pass to entrypoint
parser = argparse.ArgumentParser(description=(
    "Wait a limited time for specified codepipeline execution to complete."))

parser.add_argument('name', help='Name of codepipeline')
parser.add_argument('execution_id', help='Codepipeline Execution ID')
parser.add_argument('--wait_seconds', nargs='?', default=5, type=int,
                    help='Seconds between checks')
parser.add_argument('--attempt_count', nargs='?', default=60, type=int,
                    help='Number of times to check')
parser.add_argument('--aws_profile', help='AWS_PROFILE to use')
args = parser.parse_args()

await_codepipeline(
    name=args.name,
    execution_id=args.execution_id,
    wait_seconds=args.wait_seconds,
    attempt_count=args.attempt_count,
    aws_profile=args.aws_profile if 'aws_profile' in args else None
)
