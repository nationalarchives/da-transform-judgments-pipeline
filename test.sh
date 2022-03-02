#!/bin/bash




for dir in $(find ./lambda_functions -maxdepth 1 -mindepth 1 -type d ); do
    if [[  $(git diff origin/test HEAD^^ lambda_functions/${dir}/*.py) ]]; then
        echo "Hello"
    else
        echo "No"
    fi
done