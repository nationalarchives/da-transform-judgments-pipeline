#!/usr/bin/env bash
set -e

main() {
  if [ $# -ne 2 ]; then
    echo 'Usage: parameter_store_parameter_name new_parser_version'
    return 1
  fi

  # e.g parameter_name='dev-tfvars'
  local parameter_name="${1}"
  local new_parser_version="${2}"

  printf 'parameter_name=%s new_parser_version=%s\n' \
      "${parameter_name}" "${new_parser_version}"

  printf 'Getting parameter %s ...\n' "${parameter_name}"
  local aws_parameter_store_value
  aws_parameter_store_value="$(
    aws ssm get-parameter \
        --name "${parameter_name}" \
        --with-decryption \
        --query Parameter.Value \
        --output text
  )"

  printf 'aws_parameter_store_value\n-------------------------\n%s\n\n' \
      "${aws_parameter_store_value}"

  # Get current version
  printf 'Extracting parser version ...\n'
  
  local python_get_version="import sys
import json
print(
    json.load(sys.stdin)['image_versions']['tre_run_judgment_parser']
)"
  
  local current_parser_version
  current_parser_version="$(
    printf '%s' "${aws_parameter_store_value}" \
      | python3 -c "${python_get_version}"
  )"

  printf 'current_parser_version=%s\n' "${current_parser_version}"
  if [[ -z "${current_parser_version}" ]]; then
    printf "Can't find parser version in parameter store parameter %s\n" \
        "${parameter_name}"
    return 1
  fi

  # Check requested version update is permitted
  printf 'Checking version update permitted from %s to %s ...\n' \
      "${current_parser_version}" "${new_parser_version}"
  if ! ./check_auto_deploy_permitted.sh "${current_parser_version}" \
      "${new_parser_version}"; then
    return 1
  fi

  local python_set_version="import sys
import json
tfvar_record = json.load(sys.stdin)
new_parser_version = sys.argv[1]
if len([int(i) for i in new_parser_version.lstrip('v').split('.')]) != 3:
    raise ValueError(f'Parser version \"{new_parser_version}\" is not valid')
tfvar_record['image_versions']['tre_run_judgment_parser'] = new_parser_version
KEY_TRE_VERSION = 'tre_version'
tre_version = tfvar_record[KEY_TRE_VERSION]
tre_version_list = [int(i) for i in tre_version.lstrip('v').split('.')]
if len(tre_version_list) != 3:
  raise ValueError(f'TRE version \"{new_parser_version}\" is not valid')
tre_version_list[2] = int(tre_version_list[2]) + 1
tre_version_list_str = [str(i) for i in tre_version_list]
new_tre_version = '.'.join(tre_version_list_str)
tfvar_record[KEY_TRE_VERSION] = new_tre_version
print(json.dumps(tfvar_record, indent=2))"

  local new_value
  new_value="$(
    printf '%s' "${aws_parameter_store_value}" | \
    python3 -c "${python_set_version}" "${new_parser_version}"
  )"

  printf '\nnew_value\n---------\n%s\n\n' "${new_value}"
  printf 'Updating parameter %s ...\n' "${parameter_name}"

  if aws ssm put-parameter \
    --name "${parameter_name}" \
    --value "${new_value}" \
    --overwrite;
  then
    printf 'Parameter %s has been updated from parser version %s to %s\n' \
        "${parameter_name}" "${current_parser_version}" "${new_parser_version}"
  else
    printf 'Error updating parameter %s from parser version %s to %s\n' \
        "${parameter_name}" "${current_parser_version}" "${new_parser_version}"
    return 1
  fi
}

main "$@"
