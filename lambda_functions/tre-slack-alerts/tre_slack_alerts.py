import urllib3
import json
import os
http = urllib3.PoolManager()
def lambda_handler(event, context):
    print(dir(context))
    print(context.client_context)
    print(event)
    url = os.environ['SLACK_WEBHOOK_URL']
    env = os.environ['ENV']
    message = json.loads(event['Records'][0]['Sns']['Message'])

    execution = message['Execution']
    state_machine = message['StateMachine']
    if 'ErrorMessage' in message:
        error_type = message['ErrorType']
        error_message = message['ErrorMessage']
        final_message = "*" + "ERROR "+ "*"+ ":alert:" + "\n" +"*" + "Environment: "  + "*" + "`" + env + "`" + "\n" + "*" + "ExecutionName: " +"*" + "`" + execution+ "`" + "\n" + "*" + "StateMachine: " + "*" + "`" + state_machine + "`" + "\n" + "*" + "ErrorType: "  + "*" + "`" + error_type + "`" + "\n" + "```" + "Error Message: "+ error_message + "```"
        
        msg = {
            "channel": os.environ['SLACK_CHANNEL'],
            "username": os.environ['SLACK_USERNAME'],
            "text": final_message,
            "icon_emoji": ":x:",
        }
    else:

        final_message = "*"+"SUCCESS "+ "*" + ":white_check_mark:" + "\n" +"*" + "Environment: "  + "*" + "`" + env + "`" + "\n" + "*" + "ExecutionName: " +"*" + "`" + execution+ "`" + "\n" + "*" + "StateMachine: " + "*" + "`" + state_machine + "`"
        
        msg = {
            "channel": os.environ['SLACK_CHANNEL'],
            "username": os.environ['SLACK_USERNAME'],
            "text": final_message,
            "icon_emoji": ":white_check_mark:",
        }
    
    encoded_msg = json.dumps(msg, indent=2).encode('utf-8')
    resp = http.request('POST',url, body=encoded_msg)
    print({
        "message": final_message, 
        "status_code": resp.status, 
        "response": resp.data
    })