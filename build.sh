#!/bin/bash

set -e

echo "Looking for images to build"



for dir in $(find ./lambda_functions -maxdepth 1 -mindepth 1 -type d ); do

    if [[ -f "$dir/build_if.sh" ]]; then
        ${dir}/build_if.sh  
    fi
done


exit