#!/usr/bin/env bash
# Build specified Docker image and optionally upload it to ECR if the
# AWS_REGION argument is given.
#
# Uses files `version.sh` and `requirements.txt` in the target dir to determine
# the Docker image name, version and any associated library package(s) to build
# and install into it. A new requirements.txt file is created to install the.
# packages (using pip3 in the Dockerfile).
#
# If specified in build's version.sh, the following local and remote Python
# packages will be built and installed into the image:
# 
# * Packages stored in this repository (not yet allocated their own repository):
#   * lib/tre_lib
#   * s3_lib
# * Packages external to this repository (without their own build system):
#   * tre_event_lib : https://github.com/nationalarchives/da-transform-schemas.git
#
# Arguments:
#
# build_sub_directory_name : The sub-dir containing the Dockerfile to build
# [AWS_REGION]             : Provide target AWS region to intiate ECR upload
#                            of image Build specified local docker image.
set -e

# Function to build tre_event_lib until it is deployed to an artifact store.
#
# Copies package that is built to the dir of Dockerfile that will load it and
# adds the filename to the corresponding pip requirements file that is used to
# install it in the container.
#
# Arguments:
#
# tre_event_lib_tag : The git tag to fetch for the build
# target_lambda_dir : The target dir for the built artifact
# requirements_file : Requirements file to append built package's filename to
function build_tre_event_lib {
    if [ $# -ne 3 ]; then
        echo "Usage: tre_event_lib_tag target_lambda_dir requirements_file"
        return 1
    fi

    local tre_event_lib_tag="${1:?}"
    local target_lambda_dir="${2:?}"
    local requirements_file="${3:?}"
    local repo_name='da-transform-schemas'
    local repo_url="https://github.com/nationalarchives/${repo_name:?}.git"

    printf 'Building tre_event_lib: repo_url=%s tre_event_lib_tag=%s\n' \
        "${repo_url}" "${tre_event_lib_tag}"

    local tre_event_lib_build_dir='.tmp_tre_event_lib_build_dir'
    printf 'tre_event_lib_build_dir=%s\n' "${tre_event_lib_build_dir}"
    printf 'Removing any existing build dir\n'
    rm -rfv "${tre_event_lib_build_dir}"
    printf 'Creating new build dir\n'
    mkdir "${tre_event_lib_build_dir}"
    
    # clone into new build dir
    git -c advice.detachedHead=false \
        clone \
        --depth 1 \
        --branch "${tre_event_lib_build_tag}" \
        "${repo_url}" \
        "${tre_event_lib_build_dir}"
    
    # Run build; use () to not lose current dir; pip3 install needed for tests
    local build_root="${tre_event_lib_build_dir}/tre_event_lib"
    ls -la "${build_root}"

    ( \
        cd "${build_root}" \
        && pip3 install --requirement requirements.txt \
        && ./build.sh \
    )

    # Copy the package 'whl' file to the location the Dockerfile reads from
    local pkg_whl_file
    pkg_whl_file="$(find "${build_root}/dist" -name "*.whl")"
    printf 'Copying "%s" to "%s"' "${pkg_whl_file}" "${target_lambda_dir}"
    cp "${pkg_whl_file:?}" "${target_lambda_dir}"

    # Update the tmp build requirements file used by the Dockerfile
    local lib_whl
    lib_whl="$(basename "${pkg_whl_file}")"
    printf 'Appending "%s" to "%s"\n' "${lib_whl}" "${requirements_file}"
    printf '%s\n' "${lib_whl:?}" >> "${requirements_file}"
}

# Build specified Docker image and optionally upload it to ECR.
#
# Arguments:
# build_sub_directory_name : The sub-dir containing the Dockerfile to build
# [AWS_REGION] : Provide target AWS region to intiate ECR upload of image
function main {
    if [ $# -lt 1 ] || [ $# -gt 2 ]; then
        printf 'ERROR: Usage: build_sub_directory_name [AWS_REGION]\n' 1>&2
        exit 1
    fi

    local build_sub_dir="${1:?}"

    if [ ! -d "${build_sub_dir}" ]; then
        printf 'ERROR: directory "%s" does not exist\n' "${build_sub_dir}" 1>&2
        exit 1
    fi

    # Source Docker build environment variables
    # shellcheck source=/dev/null
    . "${build_sub_dir}/version.sh"

    # shellcheck disable=SC2154  # var imported elsewhere
    printf 'lib_build_list: %s\n' "${lib_build_list}"
    printf 'tre_event_lib_build_tag: %s\n' "${tre_event_lib_build_tag}"

    # Create temporary requirements.txt and add built whl file names
    local build_requirements="${build_sub_dir}/requirements.txt"
    if [ -f "${build_requirements}" ]; then
        local tmp_build_requirements="${build_sub_dir}/tmp-build-requirements.txt"
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
            printf '%s\n' "${lib_whl:?}" >> "${tmp_build_requirements}"
        done

        # If tre_event_lib_build_tag set, build requested tre_event_lib version
        if [ -z "${tre_event_lib_build_tag}" ]; then
            printf 'Not building tre_event_lib\n'
        else
            build_tre_event_lib \
                "${tre_event_lib_build_tag:?}" \
                "${build_sub_dir:?}" \
                "${tmp_build_requirements:?}" 
        fi

        printf 'Running: ls -l "%s"\n' "${build_sub_dir}"
        ls -l "${build_sub_dir}"
        printf 'Running: cat "%s"\n' "${tmp_build_requirements}"
        cat "${tmp_build_requirements}"
    else
        printf 'Requirements file "%s" not found\n' "${build_requirements}"
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

    local AWS_REGION="${2:?}"

    local ecr_repository_name="lambda_functions/${docker_image_name:?}"
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
    local repository_uri
    repository_uri=$(aws ecr \
        describe-repositories \
        --region "${AWS_REGION}" \
        --repository-names "${ecr_repository_name}" | \
            python3 -c "import json,sys;print(json.load(sys.stdin)['repositories'][0]['repositoryUri'])"
    )

    # Tag build image as the current and latest version for the remote repository
    local tag_version="${repository_uri}:${docker_image_tag:?}"
    local tag_latest="${repository_uri}:latest"
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
}

main "$@"
