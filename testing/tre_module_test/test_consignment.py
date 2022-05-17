import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Instantiate logger
logger = logging.getLogger(__name__)


class TestConsignment():
    def __init__(
            self,
            config: dict
    ):
        logger.info(f'TestConsignment:__init__: config={config}')
        self.consignment_ref = config['consignment-ref']
        self.s3_key_bagit = config['s3-key-bagit']
        self.s3_key_checksum = config['s3-key-checksum']
        self.tar_metadata_file = config['tar-metadata-file']
