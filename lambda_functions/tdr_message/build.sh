#!/bin/bash

set -e
iamge_name=${PWD##*/} 
echo "building" $iamge_name

current_branch=$(git branch --show-current)

if [[  $(git diff origin/$current_branch HEAD^ lambda_functions/$image_name/*.py) ]]; then
    echo "Building a new image in here"
else
    echo "Nothing to update in here"
fi
