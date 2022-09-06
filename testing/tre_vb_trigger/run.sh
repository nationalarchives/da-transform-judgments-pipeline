#!/usr/bin/env bash
set -e

main() {
  if [ $# -lt 7 ] || [ $# -gt 8 ]; then
    echo "Usage: state_machine_name s3_bucket_source s3_object_bagit \
s3_object_sha consignment_reference consignment_type \
aws_profile_source aws_profile_target"
    return 1
  fi

  local state_machine_name="${1}"
  local s3_bucket_source="${2}"
  local s3_object_bagit="${3}"
  local s3_object_sha="${4}"
  local consignment_reference="${5}"
  local consignment_type="${6}"
  local aws_profile_source="${7:-${AWS_PROFILE:?}}"
  local aws_profile_target="${8:-${AWS_PROFILE:?}}"

  local query='stateMachines[?name==`'${state_machine_name}'`].stateMachineArn'
  local state_machine_arn
  state_machine_arn="$(
    aws --profile "${aws_profile_target}" \
      stepfunctions list-state-machines \
      --query "${query}" \
      --output text
  )"
  
  printf 'state_machine_arn="%s"\n' "${state_machine_arn:?}"
  printf 'aws_profile_source="%s"\n' "${aws_profile_source}"
  printf 'aws_profile_target="%s"\n' "${aws_profile_target}"

  printf 'AWS S3 listing for source profile "%s":\n' "${aws_profile_source}"
  aws --profile "${aws_profile_source}" s3 ls
  
  printf 'AWS S3 listing for target profile "%s":\n' "${aws_profile_target}"
  aws --profile "${aws_profile_target}" s3 ls

  local bagit_url
  bagit_url="$(aws --profile "${aws_profile_source}" \
      s3 presign "s3://${s3_bucket_source}/${s3_object_bagit}" \
      --expires-in "${presigned_url_expiry_secs:-60}")"

  local bagit_checksum_url
  bagit_checksum_url="$(aws --profile "${aws_profile_source}" \
      s3 presign "s3://${s3_bucket_source}/${s3_object_sha}" \
      --expires-in "${presigned_url_expiry_secs:-60}")"

  local tdr_parameters
  tdr_parameters="$(
    ../v2_event_parameters_bagit_available.sh \
        "${consignment_reference}" \
        "${bagit_url}" \
        "${bagit_checksum_url}"
  )"

  printf 'Generated TDR parameter block:\n%s\n' "${tdr_parameters}"

  local tdr_uuid
  tdr_uuid="$(uuidgen | tr '[:upper:]' '[:lower:]')"
  local uuid_list='[{"TDR-UUID": "'"${tdr_uuid}"'"}]'
  
  message="$( \
    ../v2_event_create.sh \
      "${uuid_list}" \
      'TDR' \
      'da-transform-judgments-pipeline/testing/tre_bagit_validation/run.sh' \
      "${consignment_type}" \
      'dev' \
      'consignment-export' \
      "${tdr_parameters}"
  )"
  
  printf 'Generate input message:\n%s\n' "${message}"

  export TRE_STATE_MACHINE_ARN="${state_machine_arn}"
  export TRE_CONSIGNMENT_KEY_PATH='parameters.consignment-export.reference'
  export TRE_RETRY_KEY_PATH='parameters.consignment-export.number-of-retries'
  export PYTHONPATH='../../lambda_functions/tre-vb-trigger'
  
  AWS_PROFILE="${aws_profile_target}" python3 run.py "${message}"
}

main "$@"
