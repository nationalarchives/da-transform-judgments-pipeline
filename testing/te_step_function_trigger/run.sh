#!/usr/bin/env bash
set -e

main() {
  if [ $# -lt 9 ] || [ $# -gt 10 ]; then
    echo "Usage: s3_bucket_in s3_object_bagit s3_object_sha \
consignment_reference consignment_type number_of_retries \
presign_url_expiry_secs s3_bucket_out sfn_arn [path_prefix]"
    return 1
  fi

  s3_bucket_in="$1"
  s3_key_bagit="$2"
  s3_key_manifest="$3"
  consignment_reference="$4"
  consignment_type="$5"
  number_of_retries="$6"
  preshared_url_timeout="$7"
  s3_bucket_out="$8"
  sfn_arn="$9"

  export PYTHONPATH=../../lambda_functions/tre-step-function-trigger:../../s3_lib
  export SFN_ARN="${sfn_arn}"

  event="$(../create_preshared_url_msg.sh \
    "${s3_bucket_in}" \
    "${s3_key_bagit}" \
    "${s3_key_manifest}" \
    "${consignment_reference}" \
    "${consignment_type}" \
    "${number_of_retries}" \
    "${preshared_url_timeout}")"

  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"
  python3 test-step-function-trigger.py "${event}"
}

main "$@"
