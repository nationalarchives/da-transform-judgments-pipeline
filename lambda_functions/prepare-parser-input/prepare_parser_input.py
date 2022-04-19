#!/usr/bin/env python3
import logging
import os
import boto3
import requests
import base64
import json

from s3_lib import object_lib, common_lib

# Set global logging options; AWS environment may override this though
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Instantiate logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# defaults
KEY_ERROR = "error"
KEY_ERROR_MESSAGE = "error-message"
KEY_S3_PARSER_BUCKET = "dev-te-judgment-out"
KEY_NUM_RETRIES = "number-of-retries"

ENV_PRESIGNED_URL_EXPIRY = common_lib.get_env_var('TE_PRESIGNED_URL_EXPIRY', must_exist=True, must_have_value=True)


# ENV VARS PRODUCTION
KEY_S3_PARSER_BUCKET = os.environ.get("S3_PARSER_BUCKET", "dev-te-judgment-out")
API_ENDPOINT = os.environ.get(
    "API_ENDPOINT",
    "https://7gwnzr88s0.execute-api.eu-west-2.amazonaws.com/default/dev-te-text-parser",
)


def handler(event, context):
    """
    Given input fields `s3-bucket` and `s3-bagit-name` in `event`:

    * Copy `output-message` from the input `event` into this handler's output
    * untar s3://`s3-bucket`/`s3-bagit-name` in place with existing path prefix
    * verify checksums of extracted tar's root files using file tagmanifest-sha256.txt
    * verify checksums of extracted tar's data directory files using file manifest-sha256.txt
    * verify the number of extracted files matches the numbers in the 2 manufest files

    Expected input event format:
    event = {
        "error": False,
        "s3-bucket": "dev-te-temp",
        "s3-object-root": "consignments/judgment/TDR-2021-CF6L/0/TDR-2021-CF6L",
        "s3-bagit-name": "consignments/judgment/TDR-2021-CF6L/0/TDR-2021-CF6L.tar.gz",
        "validated-files": {
            "path": "consignments/judgment/TDR-2021-CF6L/0/TDR-2021-CF6L",
            "root": [
                "consignments/judgment/TDR-2021-CF6L/0/TDR-2021-CF6L/bag-info.txt",
                "consignments/judgment/TDR-2021-CF6L/0/TDR-2021-CF6L/manifest-sha256.txt",
                "consignments/judgment/TDR-2021-CF6L/0/TDR-2021-CF6L/bagit.txt",
                "consignments/judgment/TDR-2021-CF6L/0/TDR-2021-CF6L/file-ffid.csv",
                "consignments/judgment/TDR-2021-CF6L/0/TDR-2021-CF6L/file-metadata.csv",
                "consignments/judgment/TDR-2021-CF6L/0/TDR-2021-CF6L/file-av.csv",
            ],
            "data": ["consignments/judgment/TDR-2021-CF6L/0/TDR-2021-CF6L/data/test.docx"],
        },
        "output-message": {
            "consignment-reference": "TDR-2021-CF6L",
            "s3-bagit-url": "",
            "s3-sha-url": "",
            "consignment-type": "judgment",
            "number-of-retries": 0,
        },
    }

    Output message structure; `error-message` only present if `error` is True:

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
            "s3-bucket": "tna-out",
            "attachment-urls": [],
            "s3-output-prefix": "parsed/judgment/ABC-123/0/"
    }


        "parser-outputs" : {
            "xml": "TDR-2021-CF6L.xml",
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

    Unexpected errors propagate as exceptions.
    """
    logger.info(f'handler start: event="{event}"')

    # Output data
    output = {
        KEY_ERROR: False,
    }

    try:
        # Get input parameters
        s3_bucket = event["s3-bucket"]
        s3_bagit_name = event["s3-bagit-name"]
        logger.info(f's3_bucket="{s3_bucket}" s3_bagit_name="{s3_bagit_name}"')

        # get document from s3
        S3_resource = boto3.resource("s3")

        # get judgment filename
        path = event.get("validated-files").get("data")[0]
        filename = os.path.basename(path)

        #  copy judgment to parser bucket
        source = {
            "Bucket": s3_bucket,
            "Key": event.get("validated-files").get("data")[0],
        }
        dest = S3_resource.Bucket(KEY_S3_PARSER_BUCKET)
        dest.copy(
            source,
            f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/{filename}",
        )

        logger.info(
            f"Copying Bag-it Info into parser out bucket: {KEY_S3_PARSER_BUCKET}"
        )

        # copy bagit to parser bucket
        source = {
            "Bucket": s3_bucket,
            "Key": f"{event.get('validated-files').get('path')}/bagit.txt",
        }
        dest = S3_resource.Bucket(KEY_S3_PARSER_BUCKET)
        dest.copy(
            source,
            f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/bagit-info.txt",
        )

        logger.info("Successfully copied bagit-info.")

        # copy bagit-info to parser bucket
        source = {
            "Bucket": s3_bucket,
            "Key": f"{event.get('validated-files').get('path')}/bag-info.txt",
        }
        dest = S3_resource.Bucket(KEY_S3_PARSER_BUCKET)
        dest.copy(
            source,
            f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/bag-info.txt",
        )

        logger.info("Successfully copied bag-info.")

        # create presigned url for judgment document
        document_url = object_lib.get_s3_object_presigned_url(
                KEY_S3_PARSER_BUCKET,
                f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/{filename}",
                ENV_PRESIGNED_URL_EXPIRY)

        output["context"] = {
            "number-of-retries": event["output-message"]["number-of-retries"],
            "s3-bagit-name": "bagit-info.txt",
            "judgment-document": filename,
            "consignment-type": "judgment",
            "bag-info-txt": "bag-info.txt", 
        }

        output["parser-inputs"] = {
            "consignment-reference": event["output-message"]["consignment-reference"],
            "s3-bucket": KEY_S3_PARSER_BUCKET,
            "document-url": document_url,
            "attachment-urls": [],
            "s3-output-prefix": f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/",
        }

        logger.info("Successfully sent judgement to be parsed.")

    except Exception as e:
        output[KEY_ERROR] = True
        output[KEY_ERROR_MESSAGE] = f"{e}"
        logger.error(f"Error - {e}")

    logger.info("handler return")
    return output


def copy_s3_file(s3_resource, source_bucket, target_bucket, source_key, target_key):
    """ 
    Copy a file from one s3 bucket to another s3 bucket
    """
    source = {
        "Bucket": source_bucket,
        "Key": source_key,
    }
    dest = s3_resource.Bucket(target_bucket)
    dest.copy(
        source,
        target_key,
    )

    logger.info(f"Successfully copied file {target_key} to {target_bucket}.")


def check_file_exists(s3_resource, bucket, key):
    """
    Check a file exists in an s3 bucket
    """
    try:
        s3_resource.head_object(Bucket=bucket, Key=key)
        return True
    except Exception as e:
        # Not found
        logger.info(f"Could not find file in S3 {e}")
        return False
