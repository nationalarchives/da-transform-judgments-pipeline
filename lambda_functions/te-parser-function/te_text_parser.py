#!/usr/bin/env python3
import logging
import os
import boto3
import requests
import base64
import json

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
KEY_S3_BUCKET = "s3-bucket"
KEY_S3_PARSER_BUCKET = "dev-te-judgment-out"
KEY_S3_BAGIT_NAME = "s3-bagit-name"
KEY_S3_OBJECT_ROOT = "s3-object-root"
KEY_PARSED_FILES = "parsed-files"
KEY_NUM_RETRIES = "number-of-retries"

# ENV VARS PRODUCTION
KEY_S3_PARSER_BUCKET = os.environ.get("S3_PARSER_BUCKET", "dev-te-judgment-out")
API_ENDPOINT = os.environ.get(
    "API_ENDPOINT",
    "https://7gwnzr88s0.execute-api.eu-west-2.amazonaws.com/default/dev-te-text-parser",
)
# API_KEY = ""


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

        example response in s3

    {
        "error": False,
        "error-message": str(e),
        "output-message":  "consignment-reference"
        "s3-bucket": "s3-bucket-name...",
        "s3-bagit-name": "consignments/.../.../1/tar.gz",
        "s3-object-root": "consignments/.../.../1/...",
        "parsed-files": {
            "xml": "consignments/.../.../1/...",
            "meta": ["consignments/.../.../1/.../bag-info.txt", ... ],
            "bagit-info": ["consignments/.../.../1/.../data/doc.docx", ...]
            "judgment: [""]
        }
    }

    Unexpected errors propagate as exceptions.
    """
    logger.info(f'handler start: event="{event}"')

    # Output data
    output = {
        KEY_ERROR: False,
        KEY_S3_BUCKET: None,
        KEY_S3_OBJECT_ROOT: None,
        KEY_S3_BAGIT_NAME: None,
        KEY_PARSED_FILES: {},
    }

    try:
        # Get input parameters
        s3_bucket = event["s3-bucket"]
        s3_bagit_name = event["s3-bagit-name"]
        logger.info(f's3_bucket="{s3_bucket}" s3_bagit_name="{s3_bagit_name}"')
        output[KEY_S3_BAGIT_NAME] = s3_bagit_name

        # get document from s3
        S3 = boto3.client("s3")
        S3_resource = boto3.resource("s3")
        object_key = event.get("validated-files").get("data")[0]
        s3_object = S3.get_object(Bucket=s3_bucket, Key=object_key)
        document = s3_object["Body"].read()

        # encode body to base64
        encoded = base64.b64encode(document).decode("utf-8")
        path = event.get("validated-files").get("data")[0]
        filename = os.path.basename(path)

        data = {
            "content": encoded,
            "filename": filename,
        }

        # send request to parser
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = requests.request(
            "POST", API_ENDPOINT, headers=headers, data=json.dumps(data)
        )
        response_json = response.json()
        logger.info("response")

        output_obj = {
            "xml": response_json.get("xml", None),
            "meta": response_json.get("meta", None),
            "images": response_json.get("images", None),
        }

        logger.info("Received response from parser:", output_obj)

        logger.info("Creating XML")
        # xml
        with open(
            f'/tmp/{event["output-message"]["consignment-reference"]}-te-xml.xml', "w"
        ) as xml_file:
            xml_file.write(output_obj["xml"])
            object_key = f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/{event['output-message']['consignment-reference']}.xml"
            S3.upload_file(
                f'/tmp/{event["output-message"]["consignment-reference"]}-te-xml.xml',
                KEY_S3_PARSER_BUCKET,
                object_key,
            )

        logger.info("Creating META JSON File")
        # meta
        with open(f'/tmp/{event["output-message"]["consignment-reference"]}-te-meta.json', "w") as json_file:
            logger.info(output_obj["meta"])
            json_file.write(json.dumps(output_obj["meta"]))
            log = json.dumps(output_obj["meta"]).encode()
            object_key = f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/te-meta.json"
            bucket = S3_resource.Bucket(KEY_S3_PARSER_BUCKET)
            bucket.upload_file(
                f'/tmp/{event["output-message"]["consignment-reference"]}-te-meta.json',
                object_key,
            )
            obj = S3_resource.Object(KEY_S3_PARSER_BUCKET, object_key)
            response = obj.put(Body=log)

        logger.info(f"Copying Judgement into parser out bucket: {KEY_S3_PARSER_BUCKET}")
        #  judgment
        source = {
            "Bucket": s3_bucket,
            "Key": event.get("validated-files").get("data")[0],
        }
        dest = S3_resource.Bucket(KEY_S3_PARSER_BUCKET)
        dest.copy(
            source,
            f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/{filename}",
        )

        logger.info(f"Copying Bagit Info into parser out butkcet: {KEY_S3_PARSER_BUCKET}")
        # bagit-info
        source = {
            "Bucket": s3_bucket,
            "Key": f"{event.get('validated-files').get('path')}/bag-info.txt",
        }
        dest = S3_resource.Bucket(KEY_S3_PARSER_BUCKET)
        dest.copy(
            source,
            f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/bagit-info.txt",
        )

        logger.info("Successfully parsed judgement.")

        # place xml, meta json, bag it info in output message
        output["consignment-reference"] = event["output-message"][
            "consignment-reference"
        ]
        output["consignment-type"] = event["output-message"]["consignment-type"]
        output[KEY_S3_BUCKET] = KEY_S3_PARSER_BUCKET
        output[
            "s3-object-root"
        ] = f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}"
        output["s3-parser-bucket"] = KEY_S3_PARSER_BUCKET
        output[KEY_PARSED_FILES][
            "xml"
        ] = f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}.xml"
        output[KEY_PARSED_FILES][
            "judgment"
        ] = f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/{filename}"
        output[KEY_PARSED_FILES][
            "meta"
        ] = f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/te-meta.json"
        output[KEY_PARSED_FILES][
            "bagit-info"
        ] = f"parsed/{event['output-message']['consignment-type']}/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/bagit-info.txt"

    except Exception as e:
        output[KEY_ERROR] = True
        output[KEY_ERROR_MESSAGE] = f"{e}"
        logger.error(f"Error - {e}")

    logger.info("handler return")
    return output


def retrieve_judgment_meta():
    '''function to retrieve the meta for a judgement
    '''
    pass

def parse_judgment():
    "function to send a judgment to be parsed"
    pass

def copy_from_bucket():
    '''
    function to copy a file from one bucket to another bucket
    '''
    pass

def create_output_message(bucket=None, consignment_type=None, consignment_reference=None, retry_count=None):
    '''
    function to create an output message to be returned to editorial team
    '''
    pass
