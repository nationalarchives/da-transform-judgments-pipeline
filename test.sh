#!/bin/bash

set -e

cb=$(git branch --show-current)
git diff origin/$cb HEAD^
echo "Looking for iamges to build"

# for dir in $(find ./lambda_functions -maxdepth 1 -mindepth 1 -type d ); do
#     for file in $dir/*.sh ; do
#         if [[ -f "$file" ]]; then
#             $dir/build.sh
#         fi
#     done
# done

for dir in $(find ./lambda_functions -maxdepth 1 -mindepth 1 -type d ); do

    if [[ -f "$dir/build_if.sh" ]]; then
        ${dir}/build_if.sh  
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