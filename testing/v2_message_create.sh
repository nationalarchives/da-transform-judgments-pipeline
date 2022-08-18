#!/usr/bin/env bash
# Example use:
# foo_uuid="$(uuidgen | tr '[:upper:]' '[:lower:]')"
# uuid_list='[{"FOO_UUID": "'"${foo_uuid}"'"}]'
# ./create_v2_message "${uuid_list}" 'TRE' 'process name' 'judgment' 'dev' '{}'
set -e

function main() {
  if [ $# -lt 7 ] || [ $# -gt 8 ]; then
    echo "Usage: uuid_list producer process type environment event_name\
parameters [version]"
    return 1
  fi

  local uuid_list="${1}"
  local producer="${2}"
  local process="${3}"
  local type="${4}"
  local environment="${5}"
  local event_name="${6}"
  local parameters="${7}"
  local version="${8:-1.0.0}"

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
    "environment": "%s",
    "event-name": "%s"
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
      "${event_name}" \
      "${parameters}"
}

main "$@"
