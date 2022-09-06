#!/usr/bin/env bash
set -e

function main() {
  if [ $# -ne 3 ]; then
    echo "Usage: consignment_ref bagit_url bagit_checksum_url"
    return 1
  fi

  local consignment_ref="${1}"
  local bagit_url="${2}"
  local bagit_checksum_url="${3}"
  
  printf '    "bagit-available": {
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
      "reference": "%s"
    }\n' \
    "${bagit_url}" \
    "${bagit_checksum_url}" \
    "${consignment_ref}"
}

main "$@"
