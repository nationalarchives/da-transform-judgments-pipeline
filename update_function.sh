#!/bin/bash

set -e


for dir in $(find ./lambda_functions -maxdepth 1 -mindepth 1 -type d ); do

    if [[ -f "$dir/update_function.sh" ]]; then
        ${dir}/update_function.sh  
    fi
done


exit 