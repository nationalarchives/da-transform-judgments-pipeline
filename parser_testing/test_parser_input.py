import json
from json.tool import main
import logging
import boto3
from botocore.exceptions import ClientError

def create_presigned_url(bucket_name, object_name, expiration=3600):
    bucket_name = "dev-te-testdata"
    object_name = "parser_test_docs/AUTONOMY COMPOSITE PART A FINAL AS SEALED NOON.docx"
    # Generate a presigned URL for the S3 object
    # The response contains the presigned URL
    s3_client = boto3.client('s3')
    return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name,
                    'Key': object_name},
            ExpiresIn=expiration)


url = create_presigned_url('BUCKET_NAME', 'OBJECT_NAME')

# Prepare parser input with test document pre-signed url
parser_input = {
    "parser-inputs": {
        "consignment-reference": "TDR-2022-CF6L",
        "s3-bucket": "dev-te-testdata",
        "document-url": url,
        "attachment-urls": [],
        "s3-output-prefix": "parsed/judgment/TDR-2022-CF6L/0/"
    }
}
print(parser_input)

# Invoke parser lambda to test

client = boto3.client('lambda')
parser_response = client.invoke(
    FunctionName='test_judgment_parser',
    Payload= json.dumps(parser_input),

)
parser_output = json.load(parser_response['Payload'])

# Check if parser outputs contain any error
assert len(parser_output["parser-outputs"]["error-messages"]) < 1


def main():
    print("Hello")

    
if __name__ == "__main__":
    main()
