#!/usr/bin/env bash
set -e

main() {
  if [ $# -lt 6 ] || [ $# -gt 8 ]; then
    echo "Usage: s3_bucket_source s3_object_bagit s3_object_sha \
consignment_reference consignment_type s3_bucket_target [aws_profile_source] \
[aws_profile_target]"
    return 1
  fi

  local s3_bucket_source="$1"
  local s3_object_bagit="$2"
  local s3_object_sha="$3"
  local consignment_reference="$4"
  local consignment_type="$5"
  local s3_bucket_target="$6"
  local aws_profile_source="${7:-${AWS_PROFILE:?}}"
  local aws_profile_target="${8:-${AWS_PROFILE:?}}"

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

  local event_parameters
  event_parameters="$(
    ../v2_event_parameters_bagit_available.sh \
        "${consignment_reference}" \
        "${bagit_url}" \
        "${bagit_checksum_url}"
  )"

  printf 'Generated parameter block:\n%s\n' "${event_parameters}"

  local input_uuid
  input_uuid="$(uuidgen | tr '[:upper:]' '[:lower:]')"
  local uuid_list='[{"TDR-UUID": "'"${input_uuid}"'"}]'
  
  event="$( \
    ../v2_event_create.sh \
      "${uuid_list}" \
      'TDR' \
      'da-transform-judgments-pipeline/testing/tre_bagit_then_files_v2/run.sh' \
      "${consignment_type}" \
      'dev' \
      'bagit-available' \
      "${event_parameters}"
  )"
  
  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"

  # export PYTHONPATH=../../tre-validate-bagit:../../s3_lib
  export PYTHONPATH=../../lambda_functions/tre-vb-validate-bagit:../../lambda_functions/tre-vb-validate-bagit-files
  export TRE_ENVIRONMENT='localhost'
  export TRE_S3_BUCKET="${s3_bucket_target}"
  export TRE_SYSTEM_NAME='TRE'
  export TRE_PROCESS_NAME='tre_validate_bagit test outside of step function'
  
  AWS_PROFILE="${aws_profile_target}" python3 run.py "${event}"
}

main "$@"
