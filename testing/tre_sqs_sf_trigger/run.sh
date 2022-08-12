#!/usr/bin/env bash
set -e

main() {
  if [ $# -ne 1 ]; then
    echo "Usage: event"
    return 1
  fi

  local event="$1"
  export PYTHONPATH='../../lambda_functions/tre-sqs-sf-trigger'
  export TRE_STATE_MACHINE_ARN='some:arn:value'
  export TRE_CONSIGNMENT_KEY_PATH='parameters.TDR.reference'
  export TRE_RETRY_KEY_PATH='parameters.TDR.number-of-retries'
  
  python3 run.py "${event}"
}

main "$@"
