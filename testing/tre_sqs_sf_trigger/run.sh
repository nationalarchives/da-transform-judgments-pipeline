#!/usr/bin/env bash
# Run the tre_sqs_sf_trigger handler locally. Creates a TRE event string with
# the given message_parameters and sends this to the handler, which is
# configured to use the specified Step Function.
#
# Arguments:
# state_machine_name       : The name of the Step Function that will be run
# provider_name            : Generated message's provider name; e.g. `TRE`
# event_name               : Generated message's event name; e.g. `bagit-available`
# consignment_type         : Generated message's consignment type; e.g. `judgment`
# message_parameters       : Parameters added to generated TRE message
# consignment_ref_key_path : Where Lambda finds consignment ref in incoming
#                            message parameter block; e.g.
#                            'parameters.bagit-available.reference'
# [aws_profile_target]     : Optional AWS profile name (defaults to AWS_PROFILE)
set -e

main() {
  if [ $# -lt 6 ] || [ $# -gt 7 ]; then
    echo "Usage: state_machine_name provider_name event_name consignment_type \
message_parameters consignment_ref_key_path [aws_profile_target]"
    return 1
  fi

  local state_machine_name="${1}"
  local provider_name="${2}"
  local event_name="${3}"
  local consignment_type="${4}"
  local message_parameters="${5}"
  local consignment_ref_key_path="${6}"
  local aws_profile_target="${7:-${AWS_PROFILE:?}}"

  local query='stateMachines[?name==`'${state_machine_name}'`].stateMachineArn'
  printf 'aws_profile_target="%s"\n' "${aws_profile_target}"
  printf 'Query for State Machine "%s":\n%s\n' "${state_machine_name}" "${query}"
  
  local state_machine_arn
  state_machine_arn="$(
    aws --profile "${aws_profile_target}" \
      stepfunctions list-state-machines \
      --query "${query}" \
      --output text
  )"
  
  printf 'state_machine_arn="%s"\n' "${state_machine_arn:?}"

  local message_uuid
  message_uuid="$(uuidgen | tr '[:upper:]' '[:lower:]')"
  local uuid_list='[{"'"${provider_name}"'-UUID": "'"${message_uuid}"'"}]'
  
  message="$( \
    ../v2_event_create.sh \
      "${uuid_list}" \
      "${provider_name}" \
      'da-transform-judgments-pipeline/testing/tre_sqs_sf_trigger/run.sh' \
      "${consignment_type}" \
      'local' \
      "${event_name}" \
      "${message_parameters}"
  )"
  
  printf 'Generated input message:\n%s\n' "${message}"

  export TRE_STATE_MACHINE_ARN="${state_machine_arn}"
  export TRE_CONSIGNMENT_KEY_PATH="${consignment_ref_key_path}"
  export PYTHONPATH='../../lambda_functions/tre-sqs-sf-trigger'
  
  AWS_PROFILE="${aws_profile_target}" python3 run.py "${message}"
}

main "$@"
