#!/usr/bin/env bash
set -e

main() {
  if [ $# -lt 6 ] || [ $# -gt 6 ]; then
    echo "Usage: s3_bucket_in s3_bucket_out consignment_reference consignment_type number_of_retries"
    return 1
  fi

  s3_bucket_in="$1"
  s3_bucket_out="$2"
  consignment_reference="$3"
  consignment_type="$4"
  number_of_retries="$5"
  pre_signed_timout="$6"

  #tmp clean up
  aws s3 rm s3://dev-tre-dpsg-out/consignments/standard/TDR-2022-NQ3/test-uuid/ --recursive
  aws s3 rm s3://dev-tre-common-data/consignments/standard/TDR-2022-NQ3/test-uuid/ --recursive

  export PYTHONPATH=../../lambda_functions/tre-bagit-to-dri-sip:../../s3_lib
  export S3_DRI_OUT_BUCKET="${s3_bucket_out}"
  export TRE_PRESIGNED_URL_EXPIRY="${pre_signed_timout}"
  export TRE_PROCESS_NAME="dev-local-dpsg-process-name"
  export TRE_ENVIRONMENT="dev-local-dpsg-env-name"
  export TRE_SYSTEM_NAME="dev-local-system-name"

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
    "consignments/standard/TDR-2022-NQ3/test-uuid/TDR-2022-NQ3"

  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"

  mkdir -p /tmp/tre-test/input
  aws s3api get-object --bucket dev-te-testdata  --key consignments/standard/TDR-2022-NQ3.tar.gz TDR-2022-NQ3.tar.gz --profile tna-dev-mgmt
  tar -xf TDR-2022-NQ3.tar.gz -C /tmp/tre-test/input
  aws s3 cp --recursive /tmp/tre-test/input s3://dev-tre-common-data/consignments/standard/TDR-2022-NQ3/test-uuid

  python3 test-bagit-to-dri-sip.py "${event}"

  aws s3api get-object --bucket dev-tre-dpsg-out  --key consignments/standard/TDR-2022-NQ3/test-uuid/TDR-2022-NQ3/sip/MOCKA101Y22TBNQ3.tar.gz MOCKA101Y22TBNQ3_actual.tar.gz
  aws s3api get-object --bucket dev-tre-dpsg-out  --key consignments/standard/TDR-2022-NQ3/test-uuid/TDR-2022-NQ3/sip/MOCKA101Y22TBNQ3.tar.gz.sha256 MOCKA101Y22TBNQ3_actual.tar.gz.sha256
  mkdir -p /tmp/tre-test/actual
  tar -xf MOCKA101Y22TBNQ3_actual.tar.gz -C /tmp/tre-test/actual
  mkdir -p /tmp/tre-test/expected
  tar -xf MOCKA101Y22TBNQ3_expected2.tar.gz -C /tmp/tre-test/expected
  diff -q -s -r /tmp/tre-test/actual /tmp/tre-test/expected


  DIFF=$(diff -r /tmp/tre-test/actual /tmp/tre-test/expected)
  if [ "$DIFF" != "" ]
  then
      echo "====> NOT THE SAME ==> FAIL"
  else
      echo "  ====> SAME YAY  <====  "
  fi

  # clean up
  rm -rf /tmp/tre-test/*
  rm TDR-2022-NQ3.tar.gz
  rm MOCKA101Y22TBNQ3_actual.tar.gz
  rm MOCKA101Y22TBNQ3_actual.tar.gz.sha256
  aws s3 rm s3://dev-tre-dpsg-out/consignments/standard/TDR-2022-NQ3/test-uuid/ --recursive
  aws s3 rm s3://dev-tre-common-data/consignments/standard/TDR-2022-NQ3/test-uuid/ --recursive
}

main "$@"
