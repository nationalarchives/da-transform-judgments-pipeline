#!/usr/bin/env python3
import logging
from multiprocessing.sharedctypes import Value
from s3_lib import common_lib
from s3_lib import object_lib
from s3_lib import tar_lib
import json
import boto3

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Error class
class TEEditorialIntegrationError(Exception):
    """
    Used to indicate a te_editorial_integration step specific error condition.
    """

# Get environment variable values
env_version_info = json.loads(common_lib.get_env_var('TE_VERSION_JSON', must_exist=True, must_have_value=True))
env_presigned_url_expiry = common_lib.get_env_var('TE_PRESIGNED_URL_EXPIRY', must_exist=True, must_have_value=True)

KEY_CONTEXT = 'context'
KEY_NUMBER_OF_RETRIES='number-of-retries'
KEY_BAG_INFO = 'bag-info-txt'
KEY_JUDGMENT_DOC = 'judgment-document'
KEY_CONSIGNMENT_TYPE = 'consignment-type'

KEY_PARSER_INPUTS = 'parser-inputs'
KEY_CONSIGNMENT_REF='consignment-reference'
KEY_S3_BUCKET='s3-bucket'
KEY_S3_PREFIX='s3-output-prefix'

KEY_PARSER_OUTPUTS = 'parser-outputs'
KEY_XML = 'xml'
KEY_PARSER_METADATA = 'metadata'
KEY_IMAGES = 'images'
KEY_ATTACHMENTS = 'attachments'
KEY_LOG = 'log'
KEY_ERROR_MESSAGES = 'error-messages'

OUTPUT_MESSAGE_FILE = 'output-message.json'
PRODUCER_NAME = 'TRE'
FILE_TRE_METADATA = 'metadata.json'
KEY_CONSIGNMENT_TYPE='consignment-type'
S3_SEP = '/'
KEY_TAR_GZ = 'tar-gz'
KEY_BUCKET = 'bucket'
KEY_KEY = 'key'
KEY_PRESIGNED_TAR_GZ_URL = 's3-folder-url'
KEY_EDITORIAL_OUTPUT = 'editorial-output'

def handler(event, context):
    """
    Determine input event type (parser or retry) and process accordingly.

    Expected input event format is one of:

    * If from Parser (a list):

    [
        {
            "context" : {
                "number-of-retries": "0",
                "s3-bagit-name": "bag-info.txt",
                "judgment-document": "judgment.docx",
                "consignment-type": "judgment",
                "bagit-info": "bag-info.txt"
            },
            "parser-inputs": {
                "consignment-reference": "ABC-123",
                "s3-bucket": "...",
                "attachment-urls": [],
                "s3-output-prefix": "parsed/judgment/ABC-123/0/"
            }
        },
        {
            "parser-outputs" : {
            "xml": "ABC-123.xml",
            "metadata": "metadata.json",
            "images": [
                "world-1.png",
                "world-2.png"
            ],
            "attachments": [],
            "log": "parser.log",
            "error-messages": []
            }
        }
    ]

    * If a retry message (a dictionary):
    
    {
      "consignment-reference": "...",
      "consignment-type": "...",
      "number-of-retries": 0
    }

    Output SNS message format:

    {
      "consignment-reference": "TDR-...",
      "s3-folder-url": "...",
      "consignment-type": "judgment",
      "number-of-retries": 0
    }
    """
    logger.info(f'handler start: event="{event}"')

    # Parser output is list, retry message is dictionary
    if isinstance(event, list):
        return ParserHandler(event).process()
    elif isinstance(event, dict):
        return RetryHandler(event).process()

    raise TEEditorialIntegrationError(
        'Invalid input event; expected list (from parser) or '
        'dictionary (from retry)')

class ParserHandler:
    """
    Process parser output.
    """
    def __init__(self, event):
        """
        Initialise object from event data and perform basic validation.
        Assume Editorial retry number 0; check this has not been used in S3.
        """
        logger.info('ParserHandler.__init__ start')
        
        # Get context parameter block
        context_block = [item for item in event if KEY_CONTEXT in item and KEY_PARSER_INPUTS in item]
        logger.info(f'context_block={context_block}')
        if len(context_block) != 1:
            raise ValueError(
                f'Error locating input parameter block with keys '
                f'"{KEY_CONTEXT}" and "{KEY_PARSER_INPUTS}"; '
                f'{len(context_block)} records found')
        
        # Get parser output parameter block
        parser_output_block = [item for item in event if KEY_PARSER_OUTPUTS in item]
        logger.info(f'parser_output_block={parser_output_block}')
        if len(parser_output_block) != 1:
            raise ValueError(
                f'Error locating input parameter block with key '
                f'"{KEY_PARSER_OUTPUTS}"; {len(parser_output_block)} records found')

        # Extract and save parameter blocks
        self.context = context_block[0][KEY_CONTEXT]
        self.parser_inputs = context_block[0][KEY_PARSER_INPUTS]
        self.parser_outputs = parser_output_block[0][KEY_PARSER_OUTPUTS]
        logger.info(f'self.context={self.context}')
        logger.info(f'self.parser_inputs={self.parser_inputs}')
        logger.info(f'self.parser_outputs={self.parser_outputs}')

        # Validate
        self.validate_fields()

        # Ensure this process has not already been run
        prior_ed_attempt_latest = object_lib.get_max_s3_subfolder_number(
                self.parser_inputs[KEY_S3_BUCKET],
                self.parser_inputs[KEY_S3_PREFIX])

        if prior_ed_attempt_latest is not None:
            raise ValueError(
                f'First run of process found unexpected output folder '
                f'"{prior_ed_attempt_latest}" at path '
                f'"{self.parser_inputs[KEY_S3_PREFIX]}" in bucket '
                f'"{self.parser_inputs[KEY_S3_BUCKET]}".')

        # Set path for editorial output to be retry 0 (always zero for creation via TDR call)
        self.number_of_editorial_retries = 0
        self.s3_output_prefix_ed = (self.parser_inputs[KEY_S3_PREFIX]
            + str(self.number_of_editorial_retries) + '/')

        logger.info('ParserHandler.__init__ end')

    def validate_fields(self):
        """
        Perform validation on the input event data
        """
        logger.info('validate_fields start')

        missing_context_fields = []
        if KEY_NUMBER_OF_RETRIES not in self.context:
            missing_context_fields.append(KEY_NUMBER_OF_RETRIES)
        if KEY_BAG_INFO not in self.context:
            missing_context_fields.append(KEY_BAG_INFO)
        if KEY_JUDGMENT_DOC not in self.context:
            missing_context_fields.append(KEY_JUDGMENT_DOC)
        if KEY_CONSIGNMENT_TYPE not in self.context:
            missing_context_fields.append(KEY_CONSIGNMENT_TYPE)
        if len(missing_context_fields) > 0:
            raise TEEditorialIntegrationError(
                f'Missing mandatory context block inputs: {missing_context_fields}')

        missing_parser_input_fields = []
        if KEY_CONSIGNMENT_REF not in self.parser_inputs:
            missing_parser_input_fields.append(KEY_CONSIGNMENT_REF)
        if KEY_S3_BUCKET not in self.parser_inputs:
            missing_parser_input_fields.append(KEY_S3_BUCKET)
        if KEY_S3_PREFIX not in self.parser_inputs:
            missing_parser_input_fields.append(KEY_S3_PREFIX)
        if len(missing_parser_input_fields) > 0:
            raise TEEditorialIntegrationError(
                f'Missing mandatory parser input block inputs: {missing_parser_input_fields}')

        missing_parser_output_fields = []
        if KEY_XML not in self.parser_outputs:
            missing_parser_output_fields.append(KEY_XML)
        if KEY_PARSER_METADATA not in self.parser_outputs:
            missing_parser_output_fields.append(KEY_PARSER_METADATA)
        if KEY_IMAGES not in self.parser_outputs:
            missing_parser_output_fields.append(KEY_IMAGES)
        if KEY_LOG not in self.parser_outputs:
            missing_parser_output_fields.append(KEY_LOG)
        if KEY_ERROR_MESSAGES not in self.parser_outputs:
            missing_parser_output_fields.append(KEY_ERROR_MESSAGES)
        if len(missing_parser_output_fields) > 0:
            raise TEEditorialIntegrationError(
                f'Missing mandatory parser output block inputs: {missing_parser_output_fields}')

        logger.info('validate_fields end')

    def process(self):
        """
        * Create a tar.gz file in S3 with:
            * Generated JSON metadata file
            * Parser output files
            * Judgment doc
        * Generate a pre-shared URL for the `tar.gz` archive
        * Return JSON output with message for Editorial notification (via
          subsequent SNS step) and save this to s3 for any retry processing
        """
        logger.info('process start')

        # Build list of files to tar
        to_tar_list = []
        prefix = self.parser_inputs[KEY_S3_PREFIX]
        tre_metadata_file = self.create_tre_metadata_file()
        to_tar_list.append(tre_metadata_file)
        to_tar_list.append(prefix + self.parser_outputs[KEY_XML])
        to_tar_list.append(prefix + self.parser_outputs[KEY_LOG])
        to_tar_list.append(prefix + self.context[KEY_JUDGMENT_DOC])

        if KEY_IMAGES in self.parser_outputs:
            for image in self.parser_outputs[KEY_IMAGES]:
                to_tar_list.append(prefix + image)

        # Write the list of s3 files to the output tar
        output_tar_gz = (self.s3_output_prefix_ed + PRODUCER_NAME + '-' 
            + self.parser_inputs[KEY_CONSIGNMENT_REF] + '.tar.gz')
        logger.info(f'output_tar_gz={output_tar_gz}')
        tar_items = tar_lib.s3_objects_to_s3_tar_gz_file(
            self.parser_inputs[KEY_S3_BUCKET],
            to_tar_list,
            output_tar_gz,
            f'{self.parser_inputs[KEY_CONSIGNMENT_REF]}/')
        
        # Generate a presigned URL for the output tar.gz file
        presigned_tar_gz_url = object_lib.get_s3_object_presigned_url(
            self.parser_inputs[KEY_S3_BUCKET],
            output_tar_gz,
            env_presigned_url_expiry)

        # Create the output message
        output_message = {
            KEY_EDITORIAL_OUTPUT: {
                'consignment-reference': self.parser_inputs[KEY_CONSIGNMENT_REF],
                KEY_PRESIGNED_TAR_GZ_URL: presigned_tar_gz_url,
                'consignment-type': self.context[KEY_CONSIGNMENT_TYPE],
                'number-of-retries': self.number_of_editorial_retries
            },
            KEY_TAR_GZ: {
                KEY_BUCKET: self.parser_inputs[KEY_S3_BUCKET],
                KEY_KEY: output_tar_gz,
                'items': tar_items
            }
        }

        # Save output message (in case of Editorial retries)
        object_lib.string_to_s3_object(
            json.dumps(output_message),
            self.parser_inputs[KEY_S3_BUCKET],
            self.s3_output_prefix_ed + OUTPUT_MESSAGE_FILE)
    
        # Return output message with presigned URL
        logger.info(f'process return')
        return output_message
        
    def get_reference_prefix(self):
        """
        Use producer name + consignment reference as a prefix.
        """
        logger.info('get_reference_prefix')
        return PRODUCER_NAME + '-' + self.parser_inputs[KEY_CONSIGNMENT_REF] + '-'

    def create_tre_metadata_file(self):
        """
        Create the metadata file for the tar and return its path.
        """
        logger.info('create_tre_metadata_file start')
        output_name = self.get_reference_prefix() + FILE_TRE_METADATA
        s3_path = (self.parser_inputs[KEY_S3_PREFIX] 
            + str(self.number_of_editorial_retries) + S3_SEP + output_name)
        
        # Load parser metadata file as dictionary
        parser_metadata = self.get_parser_metadata_file()
        bagit_info_dict = object_lib.s3_object_to_dictionary(
            self.parser_inputs[KEY_S3_BUCKET],
            self.parser_inputs[KEY_S3_PREFIX] + self.context[KEY_BAG_INFO])
        
        # Create metadata dictionary
        tre_metadata = self.build_tre_metadata(output_name, parser_metadata, bagit_info_dict)

        # Save metadata to S3 object (raises error if exists)
        object_lib.string_to_s3_object(
            json.dumps(tre_metadata),
            self.parser_inputs[KEY_S3_BUCKET],
            s3_path)
        
        logger.info(f'create_tre_metadata_file return: s3_path={s3_path}')
        return s3_path

    def get_parser_metadata_file(self):
        """
        Load the Parser metadata JSON file.
        """
        logger.info('get_parser_metadata_file start')
        bucket = self.parser_inputs[KEY_S3_BUCKET]
        key = self.parser_inputs[KEY_S3_PREFIX] + self.parser_outputs[KEY_PARSER_METADATA]
        logger.info(f'get_parser_metadata_file bucket={bucket} key={key}')
        s3c = boto3.client('s3')
        s3_object = s3c.get_object(Bucket=bucket, Key=key)
        parser_metadata = json.loads(s3_object['Body'].read())
        logger.info(f'get_parser_metadata_file return {parser_metadata}')
        return parser_metadata

    def build_tre_metadata(self, filename, parser_metadata, bagit_info):
        """
        Return TRE metadata dictionary.
        """
        logger.info('build_tre_metadata start')

        parser_content = parser_metadata.copy()
        parser_content['error-messages'] = self.parser_outputs[KEY_ERROR_MESSAGES].copy()
        
        output =  {
            'producer': {
                'name': PRODUCER_NAME,
                'process': 'transform',
                'type': self.context[KEY_CONSIGNMENT_TYPE]
            },
            'parameters': {
                PRODUCER_NAME: {
                    'reference': PRODUCER_NAME + '-' + self.parser_inputs[KEY_CONSIGNMENT_REF],
                    'payload': {
                        'filename': self.context[KEY_JUDGMENT_DOC],
                        'xml': self.parser_outputs[KEY_XML],
                        'metadata': filename,
                        'images': self.parser_outputs[KEY_IMAGES],
                        'log': self.parser_outputs[KEY_LOG]
                    }
                },
                'PARSER': parser_content,
                'TDR': bagit_info.copy()
            }
        }

        logger.info('build_tre_metadata return; output={output}')
        return output

class RetryHandler:
    """
    Process retry event to send a new presigned URL.
    """
    def __init__(self, event):
        """
        Initialise object from event data and perform basic validation.
        """
        logger.info('RetryHandler.__init__ start')
        
        # Retry message has no S3 context from prior steps, fall back to env vars for this
        self.s3_bucket = common_lib.get_env_var('S3_BUCKET', must_exist=True, must_have_value=True)
        self.s3_object_root = common_lib.get_env_var('S3_OBJECT_ROOT', must_exist=True, must_have_value=True)

        # Extract and save parameter blocks
        self.event = event

        # Validate
        self.validate_fields()
        logger.info('RetryHandler.__init__ end')

    def validate_fields(self):
        """
        Perform basic validation on the input event data.
        """
        logger.info('validate_fields start')
        missing_fields = []
        if KEY_NUMBER_OF_RETRIES not in self.event:
            missing_fields.append(KEY_NUMBER_OF_RETRIES)
        if KEY_CONSIGNMENT_REF not in self.event:
            missing_fields.append(KEY_CONSIGNMENT_REF)
        if KEY_CONSIGNMENT_TYPE not in self.event:
            missing_fields.append(KEY_CONSIGNMENT_TYPE)

        if len(missing_fields) > 0:
            raise TEEditorialIntegrationError(
                f'Missing mandatory input fields: {missing_fields}')

        logger.info('validate_fields end')

    def process(self):
        """
        TODO
        """
        logger.info('process start')

        # Prior TDR stage number-of-retries is unknown when get an Editorial retry
        # message, so use the count in the TDR input path to find the latest one
        s3_tdr_root = (self.s3_object_root
            + self.event[KEY_CONSIGNMENT_TYPE] + S3_SEP
            + self.event[KEY_CONSIGNMENT_REF] + S3_SEP)
        
        latest_tdr_retry = object_lib.get_max_s3_subfolder_number(
            self.s3_bucket, s3_tdr_root)

        if latest_tdr_retry is None:
            raise TEEditorialIntegrationError('No TDR output data found')
        
        latest_tdr_retry = int(latest_tdr_retry)

        # Get last editorial retry number from S3 ("should" exist from TDR "retry" 0)
        ed_root = s3_tdr_root + str(latest_tdr_retry) + S3_SEP
        last_s3_ed_retry = object_lib.get_max_s3_subfolder_number(
            self.s3_bucket, ed_root)

        # Abort if no prior Editorial retry found (should be at least 0 from TDR stage)
        if last_s3_ed_retry is None:
            raise TEEditorialIntegrationError('No Editorial output data found')

        # Abort if message number-of-retries value is not the expected value
        expected_ed_retry = int(last_s3_ed_retry) + 1

        if int(self.event[KEY_NUMBER_OF_RETRIES]) != int(expected_ed_retry) :
            raise TEEditorialIntegrationError(
                f'Expected number-of-retries to be "{expected_ed_retry}" '
                f'but got "{self.event[KEY_NUMBER_OF_RETRIES]}"')

        # Read last message
        bucket = self.s3_bucket
        key = ed_root + str(last_s3_ed_retry) + S3_SEP + OUTPUT_MESSAGE_FILE
        logger.info(f'getting prior output_message bucket={bucket} key={key}')
        s3c = boto3.client('s3')
        s3_object = s3c.get_object(Bucket=bucket, Key=key)
        output_message = json.loads(s3_object['Body'].read())

        # Regenerate presigned URL
        presigned_tar_gz_url = object_lib.get_s3_object_presigned_url(
            bucket=output_message[KEY_TAR_GZ][KEY_BUCKET],
            key=output_message[KEY_TAR_GZ][KEY_KEY],
            expiry=env_presigned_url_expiry)

        # Update output message with new presigned URL and retry counter
        output_message[KEY_EDITORIAL_OUTPUT][KEY_PRESIGNED_TAR_GZ_URL] = presigned_tar_gz_url
        output_message[KEY_EDITORIAL_OUTPUT][KEY_NUMBER_OF_RETRIES] = expected_ed_retry

        # Save new output message (for any subsequent retries to update again)
        output_key = ed_root + str(expected_ed_retry) + S3_SEP + OUTPUT_MESSAGE_FILE
        object_lib.string_to_s3_object(
            string=json.dumps(output_message),
            target_bucket_name=output_message[KEY_TAR_GZ][KEY_BUCKET],
            target_object_name=output_key)

        logger.info('process return')
        return output_message
