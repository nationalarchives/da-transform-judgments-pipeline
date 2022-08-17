#!/usr/bin/env bash
set -e

main() {
  if [ $# -lt 5 ] || [ $# -gt 5 ]; then
    echo "Usage: s3_bucket_in s3_bucket_out consignment_reference consignment_type number_of_retries"
    return 1
  fi

  s3_bucket_in="$1"
  s3_bucket_out="$2"
  consignment_reference="$3"
  consignment_type="$4"
  number_of_retries="$5"

  #tmp clean up
  aws s3 rm s3://dev-tre-temp/consignments/standard/TDR-2022-NQ3/0/sip --recursive

  export PYTHONPATH=../../lambda_functions/tre-bagit-to-dri-sip:../../s3_lib
  export S3_DRI_OUT_BUCKET="${s3_bucket_out}"


  printf -v event '{
    "producer": {
      "type": "%s"
    },
    "parameters": {
      "TRE": {
      "reference": "%s",
      "s3-bucket": "%s",
      "number-of-retries": %s
      }
    }
  }' \
    "${consignment_type}" \
    "${consignment_reference}" \
    "${s3_bucket_in}" \
    "${number_of_retries}"

  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"
  python3 test-bagit-to-dri-sip.py "${event}"
  aws s3api get-object --bucket dev-tre-dpsg-out  --key consignments/standard/TDR-2022-NQ3/0/sip/MOCKA101Y22TBNQ3.tar.gz MOCKA101Y22TBNQ3_actual.tar.gz
  aws s3api get-object --bucket dev-tre-dpsg-out  --key consignments/standard/TDR-2022-NQ3/0/sip/MOCKA101Y22TBNQ3.tar.gz.sha256 MOCKA101Y22TBNQ3_actual.tar.gz.sha256
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
  rm MOCKA101Y22TBNQ3_actual.tar.gz
  rm MOCKA101Y22TBNQ3_actual.tar.gz.sha256
  aws s3 rm s3://dev-tre-dpsg-out/consignments/standard/TDR-2022-NQ3/0/sip --recursive
}

main "$@"
