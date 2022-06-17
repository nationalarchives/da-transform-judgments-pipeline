#!/usr/bin/env bash
set -e

main() {
  if [ $# -lt 6 ] || [ $# -gt 9 ]; then
    echo "Usage: s3_bucket_in s3_object_bagit s3_object_sha consignment_reference sfn_arn \
[consignment_type] [number_of_retries] [presign_url_expiry_secs]"
    return 1
  fi

  s3_bucket_in="$1"
  s3_object_bagit="$2"
  s3_object_sha="$3"
  consignment_reference="$4"
  sqs_arn="$5"
  sfn_arn="$6"
  consignment_type="$7"
  number_of_retries="$8"
  presign_url_expiry_secs="$9"

  export PYTHONPATH=../../lambda_functions/tre-step-function-trigger:../../s3_lib
  export SFN_ARN="${sfn_arn}"

  printf -v records '{
  "Records": [{
    "body": "{\\\"consignment-reference\\\": \\\"%s\\\", \\\"s3-bagit-url\\\": \\\"%s\\\", \\\"s3-sha-url\\\": \\\"%s\\\", \\\"consignment-type\\\": \\\"%s\\\", \\\"number-of-retries\\\": %s}",
    "eventSourceARN": "%s"
  }]
}\n' \
      "${consignment_reference}" \
      "$(aws s3 presign "s3://${s3_bucket_in}/${s3_object_bagit}" --expires-in "${presign_url_expiry_secs:-60}")" \
      "$(aws s3 presign "s3://${s3_bucket_in}/${s3_object_sha}" --expires-in "${presign_url_expiry_secs:-60}")" \
      "${consignment_type:-judgment}" \
      "${number_of_retries:-0}" \
      "${sqs_arn}"

  printf 'Generated input event:\n%s\nInvoking test...\n' "${records}"
  python3 test-step-function-trigger.py "${records}"
}

main "$@"
