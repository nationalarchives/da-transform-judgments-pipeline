#!/bin/bash

set -e

git diff origin/test HEAD^ lambda_functions/tdr_message/*.py

for dir in $(find ./lambda_functions -maxdepth 1 -mindepth 1 -type d ); do
    if [[  $(git diff origin/test HEAD^ lambda_functions/${dir}/*.py) ]]; then
        echo "Building a new image in ${dir}"
    else
        echo "Nothing to update in ${dir}"
    fi
done

exit