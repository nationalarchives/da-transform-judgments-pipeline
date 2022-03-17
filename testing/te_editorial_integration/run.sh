#!/usr/bin/env bash
main() {
  if [ $# -ne 4 ]; then
    echo "Usage: parser_bucket consignment_reference consignment_type \
presigned_url_expiry_secs"
    return 1
  fi

  local parser_bucket="$1"
  local consignment_reference="$2"
  local consignment_type="$3"
  local presigned_url_expiry_secs="$4"

  export PYTHONPATH='../../lambda_functions/te-editorial-integration:../../s3_lib'

  export S3_BUCKET="${parser_bucket}"
  export S3_OBJECT_ROOT='te_editorial_integration_test_data/parser_output/'
  export S3_FILE_PAYLOAD='test.docx'
  export S3_FILE_PARSER_XML='test.xml'
  export S3_FILE_PARSER_META='test.log'
  export S3_FILE_BAGIT_INFO='bag-info.txt'
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

  event="$(printf '{
    "consignment-reference": "%s",
    "consignment-type": "%s"
}\n' \
    "${consignment_reference}" \
    "${consignment_type}" \
)"

  printf 'Generated input event:\n%s\nInvoking test...\n' "${event}"
  python3 test_step_editorial_int.py "${event}"
}

main "$@"
