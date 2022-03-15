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

# move to env var
API_ENDPOINT = (
    "https://7gwnzr88s0.execute-api.eu-west-2.amazonaws.com/default/dev-te-text-parser"
)
API_KEY = ""

KEY_ERROR = "error"
KEY_ERROR_MESSAGE = "error-message"
KEY_S3_BUCKET = "s3-bucket"
KEY_S3_PARSER_BUCKET = "dev-te-judgment-out"
KEY_S3_BAGIT_NAME = "s3-bagit-name"
KEY_S3_OBJECT_ROOT = "s3-object-root"
KEY_PARSED_FILES = "parsed-files"
KEY_OUTPUT_MESSAGE = "output-message"
KEY_NUM_RETRIES = "number-of-retries"


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
        "s3-object-root": "consignments/judgement/TDR-2021-CF6L/0/TDR-2021-CF6L",
        "s3-bagit-name": "consignments/judgement/TDR-2021-CF6L/0/TDR-2021-CF6L.tar.gz",
        "validated-files": {
            "path": "consignments/judgement/TDR-2021-CF6L/0/TDR-2021-CF6L",
            "root": [
                "consignments/judgement/TDR-2021-CF6L/0/TDR-2021-CF6L/bag-info.txt",
                "consignments/judgement/TDR-2021-CF6L/0/TDR-2021-CF6L/manifest-sha256.txt",
                "consignments/judgement/TDR-2021-CF6L/0/TDR-2021-CF6L/bagit.txt",
                "consignments/judgement/TDR-2021-CF6L/0/TDR-2021-CF6L/file-ffid.csv",
                "consignments/judgement/TDR-2021-CF6L/0/TDR-2021-CF6L/file-metadata.csv",
                "consignments/judgement/TDR-2021-CF6L/0/TDR-2021-CF6L/file-av.csv",
            ],
            "data": ["consignments/judgement/TDR-2021-CF6L/0/TDR-2021-CF6L/data/test.docx"],
        },
        "output-message": {
            "consignment-reference": "TDR-2021-CF6L",
            "s3-bagit-url": "",
            "s3-sha-url": "",
            "consignment-type": "judgement",
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
            "bag-it-info": ["consignments/.../.../1/.../data/doc.docx", ...]
            "judgement: [""]
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
        KEY_OUTPUT_MESSAGE: None,
    }

    try:
        # Get input parameters
        s3_bucket = event["s3-bucket"]
        output[KEY_S3_BUCKET] = s3_bucket
        s3_bagit_name = event["s3-bagit-name"]
        logger.info(f's3_bucket="{s3_bucket}" s3_bagit_name="{s3_bagit_name}"')
        output[KEY_S3_BAGIT_NAME] = s3_bagit_name
        # Forward prior output-message
        output[KEY_OUTPUT_MESSAGE] = event[KEY_OUTPUT_MESSAGE].copy()

        # get document from s3
        S3 = boto3.client("s3")
        S3_resource = boto3.resource("s3")
        object_key = event.get("validated-files").get("data")[0]
        s3_object = S3.get_object(Bucket=s3_bucket, Key=object_key)
        document = s3_object["Body"].read()

        # encode body to base64
        encoded = base64.b64encode(document).decode("utf-8")
        data = {
            "content": encoded,
            "filename": "test_valid_judgment.docx",
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
            "meta": {
                "uri": response_json.get("meta").get("uri", None),
                "court": response_json.get("meta").get("court", None),
                "cite": response_json.get("meta").get("cite", None),
                "date": response_json.get("meta").get("date", None),
                "name": response_json.get("meta").get("name", None),
                "attachments": response_json.get("meta").get("attachments", None),
            },
            "images": response_json.get("images", None),
        }

        os.mkdir("tmp")
        # xml
        with open(
            f'tmp/{event["output-message"]["consignment-reference"]}-te-xml.xml', "w"
        ) as xml_file:
            xml_file.write(output_obj["xml"])
            object_key = f"parsed/judgement/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/te-xml.xml"
            S3.upload_file(
                f'tmp/{event["output-message"]["consignment-reference"]}-te-xml.xml',
                KEY_S3_PARSER_BUCKET,
                object_key,
            )

        # meta
        with open(
            f'tmp/{event["output-message"]["consignment-reference"]}-te-meta.json', "w"
        ) as json_file:
            json_file.write(json.dumps(output_obj["meta"]))
            object_key = f"parsed/judgement/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/te-meta.json"
            S3.upload_file(
                f'tmp/{event["output-message"]["consignment-reference"]}-te-meta.json',
                KEY_S3_PARSER_BUCKET,
                object_key,
            )

        #  judgement
        source = {
            "Bucket": s3_bucket,
            "Key": event.get("validated-files").get("data")[0],
        }
        dest = S3_resource.Bucket(KEY_S3_PARSER_BUCKET)
        dest.copy(
            source,
            f"parsed/judgement/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/judgment.docx",
        )

        # bagit-info
        source = {
            "Bucket": s3_bucket,
            "Key": f"{event.get('validated-files').get('path')}/bag-info.txt",
        }
        dest = S3_resource.Bucket(KEY_S3_PARSER_BUCKET)
        dest.copy(
            source,
            f"parsed/judgement/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/bagit-info.txt",
        )

        # place xml, meta json, bag it info in output message
        output["consignment-reference"] = event["output-message"][
            "consignment-reference"
        ]
        output[
            "s3-object-root"
        ] = f"parsed/judgement/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}"
        output["s3-parser-bucket"] = KEY_S3_PARSER_BUCKET
        output[KEY_PARSED_FILES][
            "xml"
        ] = f"parsed/judgement/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/te-xml.xml"
        output[KEY_PARSED_FILES][
            "judgement"
        ] = f"parsed/judgement/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/judgement.docx"
        output[KEY_PARSED_FILES][
            "meta"
        ] = f"parsed/judgement/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/te-meta.json"
        output[KEY_PARSED_FILES][
            "bagit-info"
        ] = f"parsed/judgement/{event['output-message']['consignment-reference']}/{event['output-message']['number-of-retries']}/bagit-info.txt"

    except Exception as e:
        output[KEY_ERROR] = True
        output[KEY_ERROR_MESSAGE] = f"{e}"
        logger.error(f"Error - {e}")

    logger.info("handler return")
    return output
