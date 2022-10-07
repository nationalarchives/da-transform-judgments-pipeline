#!/usr/bin/env bash
set -e

main() {
  if [ $# -lt 8 ] || [ $# -gt 8 ]; then
    echo "Usage: s3_bucket_testdata s3_bucket_in s3_bucket_out consignment_reference consignment_type batch_ref aws_profile"
    return 1
  fi

  s3_bucket_testdata="$1"
  s3_bucket_in="$2"
  s3_bucket_out="$3"
  consignment_reference="$4"
  consignment_type="$5"
  pre_signed_timout="$6"
  batch_ref="$7"
  aws_profile="$8"

  export PYTHONPATH=../../lambda_functions/tre-bagit-to-dri-sip:../../s3_lib

  export S3_DRI_OUT_BUCKET="${s3_bucket_out}"
  export TRE_PRESIGNED_URL_EXPIRY="${pre_signed_timout}"
  export TRE_PROCESS_NAME="dev-local-dpsg-process-name"
  export TRE_ENVIRONMENT="dev-local-dpsg-env-name"
  export TRE_SYSTEM_NAME="dev-local-system-name"

  TEST_UUID_DIRECTORY=/test-uuid/
  CONSIGNMENT=consignments/
  AWS_POST_TEST_PATH=${CONSIGNMENT}${consignment_type}/${consignment_reference}${TEST_UUID_DIRECTORY}
  AWS_TEST_FILE_PATH=${CONSIGNMENT}${consignment_type}/${consignment_reference}${TEST_UUID_DIRECTORY}${consignment_reference}

  #tmp clean up
  rm -rf /tmp/tre-test/*
  aws s3 rm s3://"${s3_bucket_in}"/"${AWS_POST_TEST_PATH:?}" --recursive
  aws s3 rm s3://"${s3_bucket_out}"/"${AWS_POST_TEST_PATH:?}" --recursive

  printf -v event '{
    "version": "1.0.0",
    "timestamp": 1661340417609575000,
    "UUIDs": [
      {
        "TDR-UUID": "c73e5ca7-cf87-442a-8248-e05f81361ae0"
      },
      {
        "TRE-UUID": "ec506d7f-f531-4e63-833e-841918105e41"
      },
      {
        "TRE-UUID": "3c1db304-090f-4b19-abfc-8618cc0e5875"
      }
    ],
    "producer": {
      "environment": "dev",
      "name": "TRE",
      "process": "dev-tre-validate-bagit",
      "event-name": "bagit-validated",
      "type": "%s"
    },
    "parameters": {
      "bagit-validated": {
        "reference": "%s",
        "s3-bucket": "%s",
        "s3-bagit-name": "ZZZ",
        "s3-object-root": "%s",
        "validated-files": {
          "path": "ZZZ",
          "root": [
            "ZZZ",
            "ZZZ"
          ],
          "data": [
            "zzz",
            "zzz"
          ]
        }
      }
    }
  }' \
    "${consignment_type}" \
    "${consignment_reference}" \
    "${s3_bucket_in}" \
    "${AWS_TEST_FILE_PATH}"

  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"

  mkdir -p /tmp/tre-test/input
  aws s3api get-object --bucket "${s3_bucket_testdata}"  --key ${CONSIGNMENT}"${consignment_type}"/"${consignment_reference}".tar.gz "${consignment_reference}".tar.gz --profile "${aws_profile}"
  tar -xf "${consignment_reference}".tar.gz -C /tmp/tre-test/input
  aws s3 cp --recursive /tmp/tre-test/input s3://"${s3_bucket_in}"/"${AWS_POST_TEST_PATH}"

  python3 test-bagit-to-dri-sip.py "${event}"

  aws s3api get-object --bucket "${s3_bucket_out}"  --key "${AWS_TEST_FILE_PATH}"/sip/"${batch_ref}".tar.gz "${batch_ref}"_actual.tar.gz
  aws s3api get-object --bucket "${s3_bucket_out}"  --key "${AWS_TEST_FILE_PATH}"/sip/"${batch_ref}".tar.gz.sha256 "${batch_ref}"_actual.tar.gz.sha256

  mkdir -p /tmp/tre-test/actual
  tar -xf "${batch_ref}"_actual.tar.gz -C /tmp/tre-test/actual

  mkdir -p /tmp/tre-test/expected
  aws s3api get-object --bucket "${s3_bucket_testdata}"  --key ${CONSIGNMENT}"${consignment_type}"/"${batch_ref}"_expected.tar.gz "${batch_ref}"_expected.tar.gz --profile "${aws_profile}"
  tar -xf "${batch_ref}"_expected.tar.gz -C /tmp/tre-test/expected

  diff -q -s -r /tmp/tre-test/actual /tmp/tre-test/expected


  DIFF=$(diff -r /tmp/tre-test/actual /tmp/tre-test/expected)
  if [ "$DIFF" != "" ]
  then
      TEST_RESULT="<===== TEST FAILED - FILES DO NOT MATCH =====>"
  else
      TEST_RESULT="<===== BOTH FILES MATCH - TEST PASSED =====>"
  fi

  # clean up
  rm -rf /tmp/tre-test/*
  rm "${consignment_reference}".tar.gz
  rm "${batch_ref}"_actual.tar.gz
  rm "${batch_ref}"_actual.tar.gz.sha256
  aws s3 rm s3://"${s3_bucket_in}"/"${AWS_POST_TEST_PATH}" --recursive
  aws s3 rm s3://"${s3_bucket_out}"/"${AWS_POST_TEST_PATH}" --recursive
  echo "$TEST_RESULT"
}

main "$@"

