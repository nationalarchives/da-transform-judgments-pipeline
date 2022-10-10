import urllib3
import json
import os

http = urllib3.PoolManager()
slack_webhook_url = os.environ["SLACK_WEBHOOK_URL"]
slack_channel = os.environ["SLACK_CHANNEL"]
slack_username = os.environ["SLACK_USERNAME"]
env = os.environ["ENV"]

def lambda_handler(event, context):

    """
    Pushes dead letter notifications to slack, alongside the environment, execution,
        and the triggering SQS dead letter event
    """
    print(event)
    records = event["Records"][0]
    attributes = records["attributes"]
    body = json.loads(records["body"])
    message = body["Message"]
    sns_topic = body["TopicArn"].split(":")[-1]
    source_queue = attributes["DeadLetterQueueSourceArn"].split(":")[-1]

    final_message = f"*STATUS* :red_circle: \n  *Environment* `{env}` \n The following message was sent to `{source_queue}` _*SQS Queue*_ via `{sns_topic}` _*SNS Topic*_ which lambda failed to consume. \n *Message:*\n ```{message}``` \n"


    msg = {
        "channel": slack_channel,
        "username": slack_username,
        "text": final_message
    }

    print(final_message)
    encoded_msg = json.dumps(msg, indent=2).encode("utf-8")
    resp = http.request("POST", slack_webhook_url, body=encoded_msg)
    print({"status_code": resp.status, "response": resp.data})
