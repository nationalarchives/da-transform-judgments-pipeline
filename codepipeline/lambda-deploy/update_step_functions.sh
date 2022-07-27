#!/usr/bin/env bash
set -e

function update_pipeline_step_functions() {
  # Iterate over a list of step function key lists (one list per line). Use
  # the values in each key list (a pair of comma separated strings) to update
  # the respective step function lambda variables by running script
  # update_sf_lambda_versions.py.
  #
  # Arguments:
  #
  # step_function_key_list : Defines which step function(s) will be updated;
  #                          expected format is:
  #
  #                           sf_ver_key_1,sf_lambda_ver_key_1
  #                           ...
  #                           sf_ver_key_n,sf_lambda_ver_key_n
  # target_parameter       : AWS Parameter Store parameter name
  # lambda_functions_dir   : Path to lambda_functions dir
  if [ $# -ne 3 ]; then
    printf 'Usage: update_pipeline_step_functions %s %s %s\n' \
        "step_function_key_list" "target_parameter" "lambda_functions_dir"
    return 1
  fi

  local step_function_key_list="$1"
  local target_parameter="$2"
  local lambda_functions_dir="$3"

  # Iterate over records. Append newline to input to ensure process a last row
  # with no newline. Use grep to ignore invalid/empty lines.
  # grep '^.\+,.\+'
  #       ^         : ^ = start of line
  #        .\+      : . = any char; \+ = 1+ times
  #           ,     : , = literal "," char
  #            .\+  : . = any char; \+ = 1+ times
  local record
  printf '%s\n' "${step_function_key_list}" \
      | grep '^.\+,.\+' \
      | while read -r record
  do
    printf 'record=%s\n' "${record}"
    local kv_array
    IFS=',' read -r -a kv_array <<< "${record}"
    printf 'kv_array[0]=%s kv_array[1]=%s\n' "${kv_array[0]}" "${kv_array[1]}"

    printf 'Invoking: ./update_sf_lambda_versions.py "%s" "%s" "%s" "%s"\n' \
        "${target_parameter}" \
        "${kv_array[0]}" \
        "${kv_array[1]}" \
        "${lambda_functions_dir}"

    ./update_sf_lambda_versions.py \
        "${target_parameter}" \
        "${kv_array[0]}" \
        "${kv_array[1]}" \
        "${lambda_functions_dir}"
  done
}

update_pipeline_step_functions "${@}"
