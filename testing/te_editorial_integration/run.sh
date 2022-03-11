#!/usr/bin/env bash
main() {
  if [ $# -ne 7 ]; then
    echo "Usage: parser_bucket_in bagit_path parser_bucket_out parser_path \
consignment_reference consignment_type presigned_url_expiry_secs"
    return 1
  fi

  parser_bucket_in="$1"
  bagit_path="$2"
  parser_bucket_out="$3"
  parser_path="$4"
  consignment_reference="$5"
  consignment_type="$6"
  presigned_url_expiry_secs="$7"

  export PYTHONPATH='../../lambda_functions/te-editorial-integration:../../s3_lib'
  export S3_PARSER_INPUT_BUCKET="${parser_bucket_in}"
  export S3_PARSER_OUTPUT_BUCKET="${parser_bucket_out}"
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
    "bagit-path": "%s",
    "parser-path": "%s",
    "consignment-type": "%s",
    "consignment-reference": "%s"
}\n' \
    "${bagit_path}" \
    "${parser_path}" \
    "${consignment_type}" \
    "${consignment_reference}" \
)"

  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"
  python3 test_step_editorial_int.py "${event}"
}

main "$@"
