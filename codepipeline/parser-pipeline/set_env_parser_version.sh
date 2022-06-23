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
  local current_parser_version
  current_parser_version="$(
    printf '%s' "${aws_parameter_store_value}" \
      | grep '^    tre_run_judgment_parser = "' \
      | cut -d '"' -f 2
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

  # Use sed to replace only tre_run_judgment_parser version
  local str_find='tre_run_judgment_parser = "'
  new_value="$(
    printf '%s' "${aws_parameter_store_value}" | \
    sed -e "s/\(${str_find}\)[^\"]*/\1${new_parser_version}/"
  )"
  #         s/                                                : search
  #           \(                                              : start group 1
  #                        \)                                 : end group 1
  #                          [^\"]*                           : match until "
  #                                /                          : replacement
  #                                 \1                        : group 1
  #                                                        /  : end
  # https://stackoverflow.com/a/49847921

  printf '\nnew_value\n---------\n%s\n\n' "${new_value}"
  printf 'Updating parameter %s ...\n' "${parameter_name}"

  if aws ssm put-parameter \
    --name "${parameter_name}" \
    --value "${new_value}" \
    --overwrite;
  then
    printf 'Parameter %s has been updated from %s to %s\n' \
        "${parameter_name}" "${current_parser_version}" "${new_parser_version}"
  else
    printf 'Error updating parameter %s from %s to %s\n' \
        "${parameter_name}" "${current_parser_version}" "${new_parser_version}"
    return 1
  fi
}

main "$@"
