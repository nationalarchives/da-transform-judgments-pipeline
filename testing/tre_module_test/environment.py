import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)

class Environment():
    """
    Provide access to an environment's config settings.
    """
    KEY_NAME = 'name'
    KEY_RESOURCES = 'resources'
    KEY_SQS = 'sqs'
    KEY_TRE_TDR_IN = 'tre-tdr-in'
    KEY_TRE_EDITORIAL_RETRY = 'tre-editorial-retry'
    KEY_URL = 'url'
    KEY_STEP_FUNCTIONS = 'stepFunctions'
    KEY_TRE_STATE_MACHINE = 'tre-state-machine'
    KEY_ARN = 'arn'

    def __init__(self, config):
        logger.info(f'Environment __init__ : config={config}')
        self.config = config

        if self.KEY_NAME not in config:
            raise ValueError(f'Missing config key: {self.KEY_NAME}')
        if self.KEY_RESOURCES not in config:
            raise ValueError(f'Missing config key: {self.KEY_RESOURCES}')
        if self.KEY_SQS not in config[self.KEY_RESOURCES]:
            raise ValueError(f'Missing config key: {self.KEY_RESOURCES}.{self.KEY_SQS}')
        if self.KEY_TRE_TDR_IN not in config[self.KEY_RESOURCES][self.KEY_SQS]:
            raise ValueError(f'Missing config key: {self.KEY_RESOURCES}.{self.KEY_SQS}.{self.KEY_TRE_TDR_IN}')
        if self.KEY_URL not in config[self.KEY_RESOURCES][self.KEY_SQS][self.KEY_TRE_TDR_IN]:
            raise ValueError(f'Missing config key: {self.KEY_RESOURCES}.{self.KEY_SQS}.{self.KEY_TRE_TDR_IN}.{self.KEY_URL}')

        self.env = f'{self.config[self.KEY_NAME]}'
        self.sqs_tre_tdr_in_url = self.config[self.KEY_RESOURCES][self.KEY_SQS][self.KEY_TRE_TDR_IN][self.KEY_URL]
        self.sqs_tre_editorial_retry = self.config[self.KEY_RESOURCES][self.KEY_SQS][self.KEY_TRE_EDITORIAL_RETRY][self.KEY_URL]
        self.step_function_tre_state_machine_arn = self.config[self.KEY_RESOURCES][self.KEY_STEP_FUNCTIONS][self.KEY_TRE_STATE_MACHINE][self.KEY_ARN]
        self.step_function_name = f'{self.env}-{self.KEY_TRE_STATE_MACHINE}'
        self.s3_bucket_tre_temp = f'{self.env}-tre-temp'
        self.s3_bucket_tre_editorial_judgment_out = f'{self.env}-tre-editorial-judgment-out'
        self.lambda_name_bagit_check = f'{self.env}-tre-bagit-checksum-validation'
        self.lambda_name_files_check = f'{self.env}-tre-files-checksum-validation'
        self.lambda_name_parser_input = f'{self.env}-tre-prepare-parser-input'
        self.lambda_name_parser = f'{self.env}-tre-run-judgment-parser'
        self.lambda_name_ed_int = f'{self.env}-tre-editorial-integration'
        self.lambda_name_slack_alerts = f'{self.env}-tre-slack-alerts'
