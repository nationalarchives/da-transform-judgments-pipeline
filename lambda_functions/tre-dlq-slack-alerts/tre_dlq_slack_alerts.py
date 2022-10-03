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

    body = json.loads(records["body"])
    message = body["Message"]
    source_lambda = records["eventSourceARN"].split(":")[-1]

    msg = {
        "Dead Letter in Queue\n"
        "channel": os.environ["SLACK_CHANNEL"],
        "username": os.environ["SLACK_USERNAME"],
        "Environment": env,
        "text": message,
        "lambda": source_lambda
    }

    encoded_msg = json.dumps(msg, indent=2).encode("utf-8")
    resp = http.request("POST", url, body=encoded_msg)
    print({"message": message, "status_code": resp.status, "response": resp.data})
