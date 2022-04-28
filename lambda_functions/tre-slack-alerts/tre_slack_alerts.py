import urllib3
import json
import os

http = urllib3.PoolManager()


def lambda_handler(event, context=None):
    print(event)
    url = os.environ["SLACK_WEBHOOK_URL"]
    env = os.environ["ENV"]
    message = json.loads(event["Records"][0]["Sns"]["Message"])
    msg = {}

    execution = message["Execution"]
    state_machine = message["StateMachine"]
    if "ErrorMessage" in message:
        error_type = message["ErrorType"]
        error_message = message["ErrorMessage"]
        final_message = f"*ERROR* :alert: <!here> \n*ENVIRONMENT* `{env}` \n*ExecutionName* `{execution}` \n*StateMachine* `{state_machine}` \n*ErrorType* `{error_type}` \n``` Error Message: {str(error_message)} ``` \n"

        msg = {
            "channel": os.environ["SLACK_CHANNEL"],
            "username": os.environ["SLACK_USERNAME"],
            "text": final_message,
            "icon_emoji": ":x:",
        }
    else:
        final_message = f"*SUCCESS* :white_check_mark: \n  *ENVIRONMENT* `{env}` \n*ExecutionName* `{execution}` \n*StateMachine* `{state_machine}` \n"
        if "Type" in message:
            message_type = message["Type"]
            if str(message_type) == "retry":
                print("Editorial Retry Message received")
                icon = ":retry:"
                final_message = f"*SUCCESS* {icon} \n*ENVIRONMENT* `{env}` \n*ExecutionName* `{execution}` \n*StateMachine* `{state_machine}` \n*Type* `EditorialRetry` \n"
            elif str(message_type) == "tda":
                print("TDA Message received")
                icon = ":white_check_mark:"
                final_message = f"*SUCCESS* {icon} \n*ENVIRONMENT* `{env}` \n*ExecutionName* `{execution}` \n*StateMachine* `{state_machine}` \n"

            msg = {
                "channel": os.environ["SLACK_CHANNEL"],
                "username": os.environ["SLACK_USERNAME"],
                "text": final_message,
                "icon_emoji": icon,
            }
        else:
            print("Message received")
            msg = {
                "channel": os.environ["SLACK_CHANNEL"],
                "username": os.environ["SLACK_USERNAME"],
                "text": final_message,
                "icon_emoji": ":white_check_mark:",
            }

    encoded_msg = json.dumps(msg, indent=2).encode("utf-8")
    resp = http.request("POST", url, body=encoded_msg)
    print({"message": final_message, "status_code": resp.status, "response": resp.data})
