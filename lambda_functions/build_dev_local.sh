#!/usr/bin/env bash
set -e

if [ $# -ne 1 ]; then
    printf 'ERROR: Usage: build_sub_directory_name\n'
    exit 1
fi

build_sub_dir="$1"

if [ ! -d "${build_sub_dir}" ]; then
    printf 'Error: directory "%s" does not exist\n' "${build_sub_dir}" 1>&2
    exit 1
fi

# Ensure wheel package installed, and running in a virtual environment
pip3 --require-virtualenv install wheel

# Build s3_lib package (use () to temporarily change to the package's dir)
(cd ../s3_lib && ./build.sh)

# Copy latest s3_lib build to this directory so Dockerfile can access it
s3_lib_whl_path="$(find ../s3_lib/dist/s3_lib*)"
s3_lib_whl="$(basename "${s3_lib_whl_path}")"
cp "${s3_lib_whl_path}" "${build_sub_dir}"

# Update temporary requirements.txt with build whl file's name
tmp_build_requirements="${build_sub_dir}/tmp-build-requirements.txt"
printf '\n%s\n' "${s3_lib_whl}" >> "${tmp_build_requirements}"

# Source Docker build environment variables
# shellcheck source=/dev/null
. "${build_sub_dir}/vars.sh"

# Ignore any error from the following command (by adding || true):
docker rmi "${docker_image:?}" || true
docker build --build-arg s3_lib_whl="${s3_lib_whl}" --tag "${docker_image}" "${build_sub_dir}"
rm "${build_sub_dir}/${s3_lib_whl}"
rm "${tmp_build_requirements}"
docker images 
