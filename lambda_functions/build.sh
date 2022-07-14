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

# Build s3_lib package (use () to temporarily change to the package's dir)
(cd ../s3_lib && ./build.sh)

# Copy latest s3_lib build to build directory so Dockerfile can access it
s3_lib_whl_path="$(find ../s3_lib/dist/s3_lib*)"
s3_lib_whl="$(basename "${s3_lib_whl_path}")"
cp "${s3_lib_whl_path}" "${build_sub_dir}"

# Create temporary requirements.txt and add build whl file's name
build_requirements="${build_sub_dir}/requirements.txt"
if [ -f "${build_requirements}" ]; then
    tmp_build_requirements="${build_sub_dir}/tmp-build-requirements.txt"
    cp "${build_requirements}" "${tmp_build_requirements}"
    printf '\n%s\n' "${s3_lib_whl}" >> "${tmp_build_requirements}"
    printf 'Requirements file "%s" copied to "%s" and updated\n' \
        "${build_requirements}" "${tmp_build_requirements}" 1>&2
else
    printf 'Requirements file "%s" not found\n' "${build_requirements}" 1>&2
fi

# Source Docker build environment variables
# shellcheck source=/dev/null
. "${build_sub_dir}/version.sh"

# Ignore any error from the following command (by adding || true)
docker rmi "${docker_image:?}" || true
docker build --build-arg s3_lib_whl="${s3_lib_whl}" --tag "${docker_image}" "${build_sub_dir}"
rm "${build_sub_dir}/${s3_lib_whl}"
rm "${tmp_build_requirements}"
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
