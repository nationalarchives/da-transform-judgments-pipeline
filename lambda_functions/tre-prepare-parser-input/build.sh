#!/usr/bin/env bash
set -e

# Ensure wheel package installed, and running in a virtual environment
pip3 --require-virtualenv install wheel

# Build s3_lib package (use () to temporarily change to the package's dir)
(cd ../../s3_lib && ./build.sh)

# Copy latest s3_lib build to this directory so Dockerfile can access it
s3_lib_whl_path="$(find ../../s3_lib/dist/s3_lib*)"
s3_lib_whl="$(basename "${s3_lib_whl_path}")"
cp "${s3_lib_whl_path}" .

# Create tmp-build-requirements.txt with whl file for build
cat requirements.txt > tmp-build-requirements.txt
printf '\n%s\n' "${s3_lib_whl}" >> tmp-build-requirements.txt

. ./vars.sh
# Ignore any error from the following command (by adding || true):
docker rmi "${docker_image}" || true
docker build --build-arg s3_lib_whl="${s3_lib_whl}" --tag "${docker_image}" .
rm "${s3_lib_whl_path}"
docker images 
