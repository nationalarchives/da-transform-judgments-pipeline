#!/usr/bin/env bash
######################################################################
# Locate, build and deploy ECR images for lambda functions that have a
# version not currently present in ECR.
#
# Dependencies:
#   ecr_version_filter.py script
#   The "aws" CLI command must be available
#   The AWS_PROFILE environment variable must be set for ECR access
#   The "docker" CLI command must be available
#   build.sh script
set -e
set -o pipefail

######################################################################
# Given a property file path and key name, output the key's value to
# stdout. Assumes file has one "key=value" entry per line.
function get_file_key_value() {
  if [ $# -ne 2 ]; then
    printf 'usage: get_file_key_value file key\n' 1>&2
    return 1
  fi

  local file="$1"
  local key="$2"

  if grep "^${key}=" "${file}" >/dev/null; then
    # Key found, output the value
    grep "^${key}=" "${file}" | cut -d '=' -f 2-
  else
    printf 'Key "%s" not found in file "%s"\n' "${key}" "${file}" 1>&2
    return 1
  fi
}

######################################################################
# Returns 0 (true) if image version is confirmed as not being in ECR.
# Returns 1 if image version is not in ECR. A return code of 2 or
# higher indaicates an error occured. The negation in the function
# name ("not_in") is deliberate to avoid inadvertent triggering of
# uploads on an unexpected error (i.e. in subsequent "if" statements).
function image_version_is_not_in_ecr() {
  if [ $# -ne 1 ]; then
    printf 'usage: image_version_is_in_ecr version_sh\n' 1>&2
    return 2
  fi

  local version_sh="$1"
  local name
  if ! name="$(get_file_key_value "${version_sh}" 'docker_image_name')"; then
    return 3
  fi

  local tag
  if ! tag="$(get_file_key_value "${version_sh}" 'docker_image_tag')"; then
    return 4
  fi

  printf 'Loaded image details; name="%s" tag="%s"\n' "${name}" "${tag}"
  local ecr_img_json
  if ! ecr_img_json="$( \
    aws ecr list-images \
        "--repository-name=lambda_functions/${name}" \
        --filter tagStatus=TAGGED)"
  then
    printf 'Error getting ECR image JSON for "%s"\n' "${name}" 1>&2
    
    # If error is just a "not found" execption, it's OK to return 0
    local not_found_message="^.*RepositoryNotFoundException.*${name}"
    if grep -q "${not_found_message}" <(aws ecr describe-images \
        "--repository-name=lambda_functions/${name}" 2>&1)
    then
      printf '"%s" confirmed not present (ECR list output contains "%s")\n' \
          "${name}" "${not_found_message}"
      return 0
    else
      printf 'Unable to determine status of ECR image "%s"\n' "${name}" 1>&2
      return 5
    fi
  fi

  local sep1='>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
  local sep2='<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<'
  printf 'ecr_img_json:\n%s\n%s\n%s\n' "${sep1}" "${ecr_img_json}" "${sep2}"

  local tag_list
  if ! tag_list="$(./ecr_version_filter.py --all --json "${ecr_img_json}")"
  then
    printf 'Error converting ECR image JSON to list\n' 1>&2
    return 6
  fi

  printf 'tag_list:\n%s\n%s\n%s\n' "${sep1}" "${tag_list}" "${sep2}"  
  if ! printf '%s' "${tag_list}" | grep --quiet "${tag}"
  then
    printf 'Tag "%s" for "%s" is confirmed not in ECR\n' "${tag}" "${name}"
    return 0
  fi

  printf 'Tag "%s" for "%s" is in ECR\n' "${tag}" "${name}"
  return 1
}

######################################################################
# If the requested image version is not already in ECR, build and
# deploy it to ECR.
function deploy_image_to_ecr() {
  if [ $# -ne 2 ]; then
    printf 'usage: deploy_image_to_ecr version_sh aws_region\n' 1>&2
    return 1
  fi

  local version_sh="$1"
  local aws_region="$2"
  printf 'deploy_image_to_ecr: "%s" "%s"\n' "${version_sh}" "${aws_region}"
  
  if [ ! -f "${version_sh}" ]; then
    printf 'deploy_image_to_ecr: argument version.sh is missing\n' 1>&2
    return 1
  fi

  local image_dir
  image_dir_path="$(dirname "${version_sh}")"
  image_dir="$(basename "${image_dir_path}")"
  printf 'image_dir=%s\n' "${image_dir}"

  if image_version_is_not_in_ecr "${version_sh}"; then
    printf 'Current image version is not in ECR, starting build\n'
    # Using () for temporary dir change
    (cd ../../lambda_functions && ./build.sh "${image_dir}" "${aws_region}")
  else
    if [ $? -eq 1 ]; then
      printf 'Current image version is in ECR, skipping build\n'
    else
      printf 'Error in deploy_image_to_ecr\n'
      return 1
    fi
  fi
}

######################################################################
# Find all possible images to deploy (those with a version.sh file).
function deploy_images_to_ecr() {
  if [ ! -f "$(basename "$0")" ]; then
    printf 'Must run from dir containing "%s"\n' "$0" 1>&2
    return 1
  fi

  if [ $# -ne 1 ]; then
    printf 'usage: deploy_images_to_ecr aws_region\n' 1>&2
    return 1
  fi

  local aws_region="$1"

  printf 'deploy_images_to_ecr "%s" "%s"\n' "$0" "$1"
  # "set -o pipefail" added above to catch any errors here
  local version_file_path
  find ../../lambda_functions \
      -mindepth 2 \
      -maxdepth 2 \
      -type f \
      -name version.sh \
  | while read -r version_file_path; do
    if ! deploy_image_to_ecr "${version_file_path}" "${aws_region}"; then
      printf 'Error processing "%s"\n' "${version_file_path}" 1>&2
      return 1
    fi
  done

  printf '############################################################\n'
  printf '###                     Completed OK                     ###\n'
  printf '############################################################\n'
}

######################################################################
deploy_images_to_ecr "$@"
