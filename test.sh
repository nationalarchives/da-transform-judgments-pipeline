#!/bin/bash


if [[  $(git diff origin/test HEAD^^ ) ]]; then
	echo "Hello"
else
	echo "No"
fi
