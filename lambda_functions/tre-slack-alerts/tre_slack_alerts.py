import urllib3
import json
import os

http = urllib3.PoolManager()


def lambda_handler(event, context):
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
        final_message = f"*STATUS* :alert: <!here> \n*Environment* `{env}` \n*ExecutionName* `{execution}` \n*StateMachine* `{state_machine}` \n*ErrorType* `{error_type}` \n``` Error Message: {str(error_message)} ``` \n"

        msg = {
            "channel": os.environ["SLACK_CHANNEL"],
            "username": os.environ["SLACK_USERNAME"],
            "text": final_message,
            "icon_emoji": ":red_circle:",
        }
    else:
        final_message = f"*STATUS* :white_check_mark: \n  *Environment* `{env}` \n*ExecutionName* `{execution}` \n*StateMachine* `{state_machine}` \n"
        if "Type" in message:
            message_type = message["Type"]
            if str(message_type) == "retry":
                print("Retry Message received")
                icon = ":large_green_circle:"
                final_message = f"*STATUS* {icon} \n*Environment* `{env}` \n*ExecutionName* `{execution}` \n*StateMachine* `{state_machine}` \n"
            elif str(message_type) == "message":
                print("TDA Message received")
                icon = ":large_green_circle:"
                final_message = f"*STATUS* {icon} \n*Environment* `{env}` \n*ExecutionName* `{execution}` \n*StateMachine* `{state_machine}` \n"
            elif str(message_type) == "warning":
                print("Warning Message received")
                icon = ":large_orange_circle:"
                warning_message = message["WarningMessage"]
                final_message = f"*STATUS* {icon} \n*Environment* `{env}` \n*ExecutionName* `{execution}` \n*StateMachine* `{state_machine}` \n *ErrorMessage* `{warning_message}`"

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
