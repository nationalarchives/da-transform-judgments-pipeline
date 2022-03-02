#!/bin/bash

set -e

echo "Looking for iamges to build"

for dir in $(find ./lambda_functions -maxdepth 1 -mindepth 1 -type d ); do
    if [[ -f "./lambda_functions/${dir}/build.sh" ]]; then
        ./lambda_functions/${dir}/build.sh
    fi
done

# for dir in $(find ./lambda_functions -maxdepth 1 -mindepth 1 -type d ); do
#     if [[  $(git diff origin/test HEAD^ ./lambda_functions/${dir}/*.py) ]]; then
#         echo "Building a new image in ${dir}"
#     else
#         echo "Nothing to update in ${dir}"
#     fi
# done

exit