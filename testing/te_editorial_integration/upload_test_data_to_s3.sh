#!/usr/bin/env bash
set -e

function main() {
  if [ $# -ne 1 ]; then
    echo "Usage: s3_bucket"
    return 1
  fi

  aws s3 cp \
      ./test_data \
      "s3://${1}/te_editorial_integration_test_data" \
      --recursive
}

main "$@"
