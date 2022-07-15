#!/usr/bin/env bash
set -e

main() {
  if [ $# -lt 4 ] || [ $# -gt 4 ]; then
    echo "Usage: s3_bucket consignment_reference consignment_type number_of_retries"
    return 1
  fi

  s3_bucket="$1"
  consignment_reference="$2"
  consignment_type="$3"
  number_of_retries="$4"

  export PYTHONPATH=../../lambda_functions/tre-bagit-to-dri-sip:../../s3_lib
  export S3_TEMPORARY_BUCKET="${s3_bucket}"

  printf -v event '{
    "consignment-reference": "%s",
    "consignment-type": "%s",
    "number-of-retries": %s
  }' \
    "${consignment_reference}" \
    "${consignment_type}" \
    "${number_of_retries}"


  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"
  python3 test-bagit-to-dri-sip.py "${event}"
}

main "$@"
