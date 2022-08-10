#!/usr/bin/env bash
set -e

main() {
  if [ $# -lt 7 ] || [ $# -gt 9 ]; then
    echo "Usage: s3_bucket_source \
s3_object_bagit s3_object_sha \
consignment_reference consignment_type number_of_retries \
s3_bucket_target [aws_profile_source] [aws_profile_target]"
    return 1
  fi

  local s3_bucket_source="$1"
  local s3_object_bagit="$2"
  local s3_object_sha="$3"
  local consignment_reference="$4"
  local consignment_type="$5"
  local number_of_retries="$6"
  local s3_bucket_target="$7"
  local aws_profile_source="${8:-${AWS_PROFILE:?}}"
  local aws_profile_target="${9:-${AWS_PROFILE:?}}"

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
    ../../../testing/v2_message_parameters_tdr.sh \
        "${consignment_reference}" \
        "${bagit_url}" \
        "${bagit_checksum_url}" \
        "${number_of_retries}"
  )"

  printf 'Generated TDR parameter block:\n%s\n' "${tdr_parameters}"

  local tdr_uuid
  tdr_uuid="$(uuidgen | tr '[:upper:]' '[:lower:]')"
  local uuid_list='[{"TDR-UUID": "'"${tdr_uuid}"'"}]'
  
  event="$( \
    ../../../testing/v2_message_create.sh \
      "${uuid_list}" \
      'TDR' \
      'consignment-export' \
      "${consignment_type}" \
      'dev' \
      "${tdr_parameters}"
  )"
  
  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"

  # export PYTHONPATH=../../tre-validate-bagit:../../s3_lib
  export PYTHONPATH=../../tre-validate-bagit
  export TRE_ENVIRONMENT='localhost'
  export TRE_S3_BUCKET="${s3_bucket_target}"
  export TRE_SYSTEM_NAME='TRE'
  export TRE_PROCESS_NAME='tre_validate_bagit test outside of step function'
  
  AWS_PROFILE="${aws_profile_target}" python3 run.py "${event}"
}

main "$@"
