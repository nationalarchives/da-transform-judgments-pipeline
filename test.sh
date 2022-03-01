#!/bin/bash


if [[  $(git diff origin/test HEAD^^ lambda_functions/tdr_message/*.py) ]]; then
	echo "Hello"
else
	echo "No"
fi
