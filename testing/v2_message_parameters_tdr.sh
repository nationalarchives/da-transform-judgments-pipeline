#!/usr/bin/env bash
set -e

function main() {
  if [ $# -lt 3 ] || [ $# -gt 4 ]; then
    echo "Usage: consignment_ref bagit_url bagit_checksum_url [number_of_retries]"
    return 1
  fi

  local consignment_ref="${1}"
  local bagit_url="${2}"
  local bagit_checksum_url="${3}"
  local number_of_retries="${4:-0}"
  
  printf '    "consignment-export": {
      "resource": {
        "resource-type": "Object",
        "access-type": "url",
        "value": "%s"
      },
      "resource-validation": {
        "resource-type": "Object",
        "access-type": "url",
        "validation-method": "SHA256",
        "value": "%s"
      },
      "number-of-retries": %s,
      "reference": "%s"
    }\n' \
    "${bagit_url}" \
    "${bagit_checksum_url}" \
    "${number_of_retries}" \
    "${consignment_ref}"
}

main "$@"
