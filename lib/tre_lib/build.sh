#!/usr/bin/env bash
set -e

# Remove local build files to ensure clean environment
printf 'Removing local build files\n'
rm -rf build/
rm -rf dist/
rm -rf tre_lib.egg-info/

# Check tests pass
printf 'Running Python tests\n'
(cd tre_lib && python3 -m unittest discover ./tests -p 'test_*.py')

# Build package .whl file in ./dist/
. version.sh
printf 'Building package: TRE_LIB_VERSION=%s\n' "${TRE_LIB_VERSION}"
python3 setup.py bdist_wheel

printf -- '--- output -------------------------------------------------\n'
find ./dist -name '*.whl'
printf -- '------------------------------------------------------------\n'
