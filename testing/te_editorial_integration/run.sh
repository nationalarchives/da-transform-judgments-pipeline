#!/usr/bin/env bash
# Runs the editorial integration step using the specified template file as the
# Lambda function's input event (JSON object).
#
# Script arguments:
#   s3_bucket                 : Name of S3 bucket holding test data
#   s3_path_prefix            : e.g. te_editorial_integration_test_data/parser_output/
#   consignment_reference     : e.g. ABC-1234
#   consignment_type          : e.g. judgment
#   number_of_retries         : 0 for TDR, 1+ for editorial retry
#   presigned_url_expiry_secs : e.g. 60
#   template                  : event template; e.g.:
#                               * function_input.json
#                               * function_input_retry.json
main() {
  if [ $# -ne 7 ]; then
    echo "Usage: s3_bucket s3_path_prefix consignment_reference consignment_type \
number_of_retries presigned_url_expiry_secs template"
    return 1
  fi

  export PYTHONPATH='../../lambda_functions/tre-editorial-integration:../../s3_lib'

  local s3_bucket="$1"
  local s3_path_prefix="$2"
  local consignment_reference="$3"
  local consignment_type="$4"
  local number_of_retries="$5"
  local template="$7"

  export S3_BUCKET="${s3_bucket}"
  export S3_OBJECT_ROOT="${s3_path_prefix}"
  export TRE_ENV="foo"
  export TRE_PREFIX="tre"
  export TRE_PRESIGNED_URL_EXPIRY="$6"
  export TRE_VERSION="1.2.3"
  export TRE_VERSION_JSON='{
  "lambda-functions-version": [
    {"bar-tre-bagit-checksum-validation" : "0.0.1"},
    {"bar-tre-files-checksum-validation" : "0.0.2"},
    {"bar-text-prepare-parser-input" : "0.0.3"},
    {"bar-text-run-judgment-parser" : "v0.5.4"},
    {"bar-text-slack-alerts" : "0.0.5"}
  ]
}'

  local event
  event="$(sed \
    -e "s/\${s3_bucket}/${s3_bucket}/" \
    -e "s+\${s3_path_prefix}+${s3_path_prefix}+" \
    -e "s/\${consignment_reference}/${consignment_reference}/" \
    -e "s/\${consignment_type}/${consignment_type}/" \
    -e "s/\${number_of_retries}/${number_of_retries}/" \
    "${template}")"
  
  printf 'event=%s\n' "${event}"
  python3 test_step_editorial_int.py "${event}"
}

main "$@"
