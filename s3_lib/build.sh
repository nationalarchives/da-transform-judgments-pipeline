#!/usr/bin/env bash
set -e

# Remove local build files to ensure clean environment
rm -rf build/
rm -rf dist/
rm -rf __pycache__/
rm -rf s3_lib/__pycache__/
rm -rf s3_lib/s3_lib.egg-info/

# Build package .whl file in ./dist/
. version.sh
printf 'Building package: S3_LIB_VERSION=%s\n' "${S3_LIB_VERSION}"
python3 setup.py bdist_wheel
