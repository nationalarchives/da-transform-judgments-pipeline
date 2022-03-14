#!/usr/bin/env bash
main() {
  if [ $# -ne 5 ]; then
    echo "Usage: parser_bucket object_root consignment_reference \
consignment_type presigned_url_expiry_secs"
    return 1
  fi

  local parser_bucket="$1"
  local object_root="$2"
  local consignment_reference="$3"
  local consignment_type="$4"
  local presigned_url_expiry_secs="$5"

  export PYTHONPATH='../../lambda_functions/te-editorial-integration:../../s3_lib'
  export TE_PRESIGNED_URL_EXPIRY="${presigned_url_expiry_secs}"
  export TE_VERSION_JSON='{
  "int-te-version" : "1.0.0",
  "text-parser-version" : "v0.2",
  "lambda-functions-version": [
    {"int-te-bagit-checksum-validation" : "0.0.4"},
    {"int-te-files-checksum-validation" : "0.0.6"},
    {"int-text-parser-version" : "v0.2"}
  ]
}'

  # event="$(create_event_json("${parser_path}"))"
  event="$(printf '{
    "s3-bucket-name": "%s",
    "s3-object-root": "%s",
    "consignment-reference": "%s",
    "consignment-type": "%s",
    "parsed-files": {
        "judgement": "te_editorial_integration_test_data/parser_output/test.docx",
        "xml": "te_editorial_integration_test_data/parser_output/test.xml",
        "bag-it-info": "te_editorial_integration_test_data/parser_output/bag-info.txt"
    }
}\n' \
    "${parser_bucket}" \
    "${object_root}" \
    "${consignment_reference}" \
    "${consignment_type}" \
)"

  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"
  python3 test_step_editorial_int.py "${event}"
}

main "$@"
