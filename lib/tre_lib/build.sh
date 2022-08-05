#!/usr/bin/env bash
set -e

# Remove local build files to ensure clean environment
printf 'Removing local build files\n'
rm -rf build/
rm -rf dist/
rm -rf __pycache__/
rm -rf s3_lib/__pycache__/
rm -rf s3_lib/s3_lib.egg-info/

# Check tests pass
printf 'Running Python tests\n'
(cd tre_lib && python3 -m unittest)

# Build package .whl file in ./dist/
. version.sh
printf 'Building package: TRE_LIB_VERSION=%s\n' "${TRE_LIB_VERSION}"
python3 setup.py bdist_wheel

printf -- '--- output -------------------------------------------------\n'
find ./dist -name '*.whl'
printf -- '------------------------------------------------------------\n'
