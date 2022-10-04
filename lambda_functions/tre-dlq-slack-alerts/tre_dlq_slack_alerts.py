import urllib3
import json
import os

http = urllib3.PoolManager()


def lambda_handler(event, context):
    """
    Pushes dead letter notifications to slack, alongside the environment, execution,
     and the triggering SQS dead letter event
    """

    url = os.environ["SLACK_WEBHOOK_URL"]
    env = os.environ["ENV"]
    
    records = event["Records"][0]
    print(records)
    
    attributes = records["attributes"]

    body = json.loads(records["body"])
    message = body["Message"]
    print(message)
    
    source_queue = attributes["DeadLetterQueueSourceArn"].split(":")[-1]

    final_message = f"*STATUS* :red_circle: \n  *Environment* `{env}` \n There is a message in `{source_queue}` which lambda failed to consume. \n ```{message}```\n"
    
    msg = {
        "channel": os.environ["SLACK_CHANNEL"],
        "username": os.environ["SLACK_USERNAME"],
        "text": final_message
    }

    print(final_message)
    encoded_msg = json.dumps(msg, indent=2).encode("utf-8")
    resp = http.request("POST", url, body=encoded_msg)
    print({"status_code": resp.status, "response": resp.data})
