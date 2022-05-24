#!/usr/bin/env bash
main() {
  if [ $# -ne 1 ]; then
    echo 'Usage: s3_bucket'
    return 1
  fi

  export PYTHONPATH='../../lambda_functions/te-editorial-integration:../../s3_lib'
  export PARSER_TEST_S3_BUCKET="${1}"
  export PARSER_TEST_S3_PATH_DATA_OK='parser/ok/'
  export PARSER_TEST_S3_PATH_DATA_FAIL='parser/fail/'
  export PARSER_TEST_S3_PATH_OUTPUT='parser/output-tmp/'
  export PARSER_TEST_TESTDATA_SUFFIX='.docx'
  export PARSER_TEST_LAMBDA='test_judgment_parser'

  python3 test_parser_lambda_fn.py
}

main "$@"
