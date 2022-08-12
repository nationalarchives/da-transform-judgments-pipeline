#!/usr/bin/env bash
# Example use:
# foo_uuid="$(uuidgen | tr '[:upper:]' '[:lower:]')"
# uuid_list='[{"FOO_UUID": "'"${foo_uuid}"'"}]'
# ./create_v2_message "${uuid_list}" 'TRE' 'process name' 'judgment' 'dev' '{}'
set -e

function main() {
  if [ $# -lt 6 ] || [ $# -gt 7 ]; then
    echo "Usage: uuid_list producer process type environment parameters [version]"
    return 1
  fi

  local uuid_list="${1}"
  local producer="${2}"
  local process="${3}"
  local type="${4}"
  local environment="${5}"
  local parameters="${6}"
  local version="${7:-1.0.0}"

  local ns_utc
  ns_utc="$(python3 -c 'import time; print(time.time_ns())')"
  
  printf '{
  "version": "%s",
  "timestamp": %s,
  "UUIDs": %s,
  "producer": {
    "name": "%s",
    "process": "%s",
    "type": "%s",
    "environment": "%s"
  },
  "parameters": {
%s
  }
}\n' \
      "${version}" \
      "${ns_utc}" \
      "${uuid_list}" \
      "${producer}" \
      "${process}" \
      "${type}" \
      "${environment}" \
      "${parameters}"
}

main "$@"
