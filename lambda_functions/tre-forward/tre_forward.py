from email import message
import boto3
import json
import os

sns = boto3.client('sns')
tre_out_topic_arn = os.environ['TRE_OUT_TOPIC_ARN']

def lambda_handler(event, context):
    print(event)
    record = event['Records'][0]
    message = json.loads(record['body']['Message'])

    response = sns.publish(
        TopicArn = tre_out_topic_arn,
        Message = json.dumps(message)
    )
    print(response)
