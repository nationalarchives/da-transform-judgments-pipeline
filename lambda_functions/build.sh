#!/usr/bin/env bash
# Build local docker image; only upload to ECR if AWS_REGION argument is given
set -e

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    printf 'ERROR: Usage: build_sub_directory_name [AWS_REGION]\n'
    exit 1
fi

build_sub_dir="$1"

if [ ! -d "${build_sub_dir}" ]; then
    printf 'Error: directory "%s" does not exist\n' "${build_sub_dir}" 1>&2
    exit 1
fi

# Source Docker build environment variables
# shellcheck source=/dev/null
. "${build_sub_dir}/version.sh"

# shellcheck disable=SC2154  # var imported elsewhere
printf 'lib_build_list: %s\n' "${lib_build_list}"

# Create temporary requirements.txt and add built whl file names
build_requirements="${build_sub_dir}/requirements.txt"
if [ -f "${build_requirements}" ]; then
    tmp_build_requirements="${build_sub_dir}/tmp-build-requirements.txt"
    printf 'Creating new "%s" file from "%s"\n' \
        "${tmp_build_requirements}" "${build_requirements}" 1>&2
    cp "${build_requirements}" "${tmp_build_requirements}"

    # Ensure there's a newline before appending .whl file list
    printf '\n' >> "${tmp_build_requirements}"

    # Build any required Python libraries (using lib_build_list in version.sh)
    for lib_name in "${lib_build_list[@]}"; do
        printf 'Building required lib: "%s"\n' "${lib_name}"
        (cd "../${lib_name}" && ./build.sh)
        lib_whl_path="$(find "../${lib_name}/dist" -name "*.whl")"
        lib_whl="$(basename "${lib_whl_path}")"
        printf 'lib_whl_path=%s lib_whl=%s\n' "${lib_whl_path}" "${lib_whl}"
        printf 'Copying "%s" to "%s"\n' "${lib_whl_path}" "${build_sub_dir}"
        cp "${lib_whl_path:?}" "${build_sub_dir}"
        printf '%s\n' "${lib_whl}" >> "${tmp_build_requirements}"
    done

    printf 'Running: ls -l "%s"\n' "${build_sub_dir}"
    ls -l "${build_sub_dir}"
    printf 'Running: cat "%s"\n' "${tmp_build_requirements}"
    cat "${tmp_build_requirements}"
else
    printf 'Requirements file "%s" not found\n' "${build_requirements}" 1>&2
fi

printf 'Running docker rmi for image "%s"\n' "${docker_image:?}"
docker rmi "${docker_image:?}" || true

printf 'Running docker build for directory "%s with tag "%s"\n' \
    "${build_sub_dir}" "${docker_image:?}"

docker build \
    --tag "${docker_image:?}" \
    "${build_sub_dir}"

docker images

# Exit with error at this point if AWS_REGION not passed to abort ECR updates
if [[ -z "$2" ]]; then
    printf 'Aborting build before ECR upload; AWS_REGION not specified\n' 1>&2
    exit 1
fi

AWS_REGION="${2:?}"

ecr_repository_name="lambda_functions/${docker_image_name:?}"
printf 'Creating ECR repository "%s"\n' "${ecr_repository_name}"

# Create ECR repository
if [[ $(aws ecr describe-repositories \
    --region "${AWS_REGION}" \
    --repository-names "${ecr_repository_name}" \
) ]]; then
    printf 'Repository "%s" already exists' "${ecr_repository_name}"
else
    aws ecr create-repository \
        --region "${AWS_REGION}"  \
        --repository-name "${ecr_repository_name}" \
        --image-scanning-configuration \
        scanOnPush=true
fi

# Get ECR repository's URI
repository_uri=$(aws ecr \
    describe-repositories \
    --region "${AWS_REGION}" \
    --repository-names "${ecr_repository_name}" | \
        python3 -c "import json,sys;print(json.load(sys.stdin)['repositories'][0]['repositoryUri'])"
)

# Tag build image as the current and latest version for the remote repository
tag_version="${repository_uri}:${docker_image_tag:?}"
tag_latest="${repository_uri}:latest"
printf 'Tagging "%s" as "%s"\n' "${docker_image}" "${tag_version}"
docker tag "${docker_image}" "${tag_version}"
printf 'Tagging "%s" as "%s"\n' "${docker_image}" "${tag_latest}"
docker tag "${docker_image}" "${tag_latest}"

# Docker login for remote ECR
aws ecr get-login-password --region "${AWS_REGION}" \
    | docker login \
        --username AWS \
        --password-stdin \
        "${repository_uri}"

# Push tagged images
printf 'Pushing "%s"\n' "${tag_version}"
docker push "${tag_version}"
printf 'Pushing "%s"\n' "${tag_latest}"
docker push "${tag_latest}"
