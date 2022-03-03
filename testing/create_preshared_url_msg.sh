#!/usr/bin/env bash
set -e

function main() {
  if [ $# -lt 3 ] || [ $# -gt 7 ]; then
    echo "Usage: s3_bucket s3_object_bagit s3_object_sha \
[consignment_reference] [consignment_type] [number_of_retries] \
[presign_url_expiry_secs]"
    return 1
  fi

  local s3_bucket="$1"
  local s3_object_bagit="$2"
  local s3_object_sha="$3"
  local consignment_reference="$4"
  local consignment_type="$5"
  local number_of_retries="$6"
  local presign_url_expiry_secs="$7"

  printf '{
    "consignment-reference": "%s",
    "s3-bagit-url": "%s",
    "s3-sha-url": "%s",
    "consignment-type": "%s",
    "number-of-retries": %s
}\n' \
      "${consignment_reference}" \
      "$(aws s3 presign "s3://${s3_bucket}/${s3_object_bagit}" --expires-in "${presign_url_expiry_secs:-60}")" \
      "$(aws s3 presign "s3://${s3_bucket}/${s3_object_sha}" --expires-in "${presign_url_expiry_secs:-60}")" \
      "${consignment_type:-judgement}" \
      "${number_of_retries:-0}"
}

main "$@"
