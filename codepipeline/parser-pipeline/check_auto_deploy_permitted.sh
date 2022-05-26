#!/usr/bin/env bash
set -e

main() {
  if [ $# -ne 2 ]; then
    echo 'Usage: version_old version_new'
    return 1
  fi

  v_old_in="${1}"
  v_new_in="${2}"

  # Use tr to remove any v prefix (it's OK if other v characters get dropped)
  local v_old
  v_old="$(printf '%s' "${v_old_in}" | tr -d 'v')"
  local v_new
  v_new="$(printf '%s' "${v_new_in}" | tr -d 'v')"

  local tmp
  tmp="$(echo "${v_old}" | awk '{split($0, values, "."); print values[1]}')"
  local v_old_major="${tmp:-0}"
  tmp="$(echo "${v_old}" | awk '{split($0, values, "."); print values[2]}')"
  local v_old_minor="${tmp:-0}"
  tmp="$(echo "${v_old}" | awk '{split($0, values, "."); print values[3]}')"
  local v_old_patch="${tmp:-0}"
  local v_old_parsed="${v_old_major}.${v_old_minor}.${v_old_patch}"

  tmp="$(echo "${v_new}" | awk '{split($0, values, "."); print values[1]}')"
  local v_new_major="${tmp:-0}"
  tmp="$(echo "${v_new}" | awk '{split($0, values, "."); print values[2]}')"
  local v_new_minor="${tmp:-0}"
  tmp="$(echo "${v_new}" | awk '{split($0, values, "."); print values[3]}')"
  local v_new_patch="${tmp:-0}"
  local v_new_parsed="${v_new_major}.${v_new_minor}.${v_new_patch}"

  local version_msg="(${v_old_parsed} -> ${v_new_parsed})"

  printf 'v_old_in=%s v_new_in=%s\n' "${v_old_in}" "${v_new_in}"
  printf 'v_old=%s v_new=%s\n' "${v_old}" "${v_new}"
  printf 'v_old_major=%s v_old_minor=%s v_old_patch=%s\n' "${v_old_major}" "${v_old_minor}" "${v_old_patch}"
  printf 'v_new_major=%s v_new_minor=%s v_new_patch=%s\n' "${v_new_major}" "${v_new_minor}" "${v_new_patch}"

  if (( v_new_major != v_old_major )); then
    printf 'Automatic major version change is not permitted %s\n' "${version_msg}"
    return 1
  fi

  if (( (v_new_major == v_old_major) && (v_new_minor == v_old_minor) && (v_new_patch == v_old_patch) )); then
    printf 'Automatic redeployment of the same parser version is not allowed %s\n' "${version_msg}"
    return 1
  fi

  if (( (v_new_minor < v_old_minor) || ( (v_new_minor == v_old_minor) && (v_new_patch < v_old_patch) ) )); then
    printf 'Automatic downgrade of parser version is not permitted %s\n' "${version_msg}"
    return 1
  fi

  printf 'Automatic upgrade of parser version may proceed %s\n' "${version_msg}"
}

main "$@"
