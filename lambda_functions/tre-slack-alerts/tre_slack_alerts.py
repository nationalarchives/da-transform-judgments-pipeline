import urllib3
import json
import os

http = urllib3.PoolManager()


def lambda_handler(event, context):
    """
    status can be either warning / success / error
    """
    print(event)
    url = os.environ["SLACK_WEBHOOK_URL"]
    env = os.environ["ENV"]
    message = json.loads(event["Records"][0]["Sns"]["Message"])
    msg = {}

    execution = message["Execution"]
    state_machine = message["StateMachine"]
    message_event = message["Event"]
    final_message = f"*STATUS* :o: \n  *Environment* `{env}` \n*ExecutionName* `{execution}` \n*StateMachine* `{state_machine}` \n"

    if "Status" in message:
        status = message["Status"]
        if str(status) == "success":
            print("Success Message received")
            icon = ":large_green_circle:"
            final_message = f"*STATUS* {icon} \n*Environment:* `{env}`\n*Event:* `{message_event}`\n*ExecutionName:* `{execution}`\n*StateMachine:* `{state_machine}`"
        elif str(status) == "warning":
            print("Warning Message received")
            icon = ":large_orange_circle:"
            error_message = message.get("ErrorMessage", "")
            final_message = f"*STATUS* {icon} \n*Environment:* `{env}`\n*Event:* `{message_event}`\n*ExecutionName:* `{execution}`\n*StateMachine:* `{state_machine}`\n*ErrorMessage:*\n```{error_message}```"
        else:
            print("Error Message received")
            icon = ":red_circle:"
            error_message = message.get("ErrorMessage", "")
            final_message = f"*STATUS* {icon} \n*Environment:* `{env}`\n*Event:* `{message_event}`\n*ExecutionName:* `{execution}`\n*StateMachine:* `{state_machine}`\n*ErrorMessage:*\n```{error_message}```"
    msg = {
        "channel": os.environ["SLACK_CHANNEL"],
        "username": os.environ["SLACK_USERNAME"],
        "text": final_message,
        "icon_emoji": icon,
    }

    encoded_msg = json.dumps(msg, indent=2).encode("utf-8")
    resp = http.request("POST", url, body=encoded_msg)
    print({"message": final_message, "status_code": resp.status, "response": resp.data})
