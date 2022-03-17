#!/usr/bin/env bash
set -e

main() {
  if [ $# -lt 8 ] || [ $# -gt 9 ]; then
    echo "Usage: s3_bucket_in s3_object_bagit s3_object_sha \
consignment_reference consignment_type number_of_retries \
presign_url_expiry_secs s3_bucket_out [path_prefix]"
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

  export PYTHONPATH=../../lambda_functions/te-bagit-checksum-validation:../../lambda_functions/te-files-checksum-validation:../../s3_lib
  export S3_TEMPORARY_BUCKET="${s3_bucket_out}"

  event="$(../create_preshared_url_msg.sh \
    "${s3_bucket_in}" \
    "${s3_key_bagit}" \
    "${s3_key_manifest}" \
    "${consignment_reference}" \
    "${consignment_type}" \
    "${number_of_retries}" \
    "${preshared_url_timeout}")"

  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"
  python3 test-bagit-then-files.py "${event}"
}

main "$@"
