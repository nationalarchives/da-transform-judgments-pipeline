#!/bin/bash




for dir in $(find ../da-transform-judgement-pipeline/lambda_functions -maxdepth 1 -mindepth 1 -type d ); do
    if [[ -f "../da-transform-judgement-pipeline/lambda_functions/${dir}" ]]; then
        if [[  $(git diff origin/test HEAD^^ ../da-transform-judgement-pipeline/lambda_functions/${dir}/*.py) ]]; then
	        echo "Hello"
        else
	        echo "No"
        fi
    fi
done