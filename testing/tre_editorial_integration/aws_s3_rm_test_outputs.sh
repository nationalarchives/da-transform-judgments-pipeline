#!/usr/bin/env bash
set -e

function main() {
  if [ $# -ne 1 ]; then
    echo "Usage: s3_bucket"
    return 1
  fi

  local s3_prefix='/te_editorial_integration_test_data/parser_output/judgment/ABC-123/0/'
  aws s3 rm "s3://${1}${s3_prefix}3/" --recursive
  aws s3 rm "s3://${1}${s3_prefix}2/" --recursive
  aws s3 rm "s3://${1}${s3_prefix}1/" --recursive
  aws s3 rm "s3://${1}${s3_prefix}0/" --recursive
}

main "$@"
