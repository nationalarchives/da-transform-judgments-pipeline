#!/bin/bash

set -e
source_path=$(which $0)

dir_name=$(dirname $source_path)
echo $dir_name
basename $dir_name
image_name=$(basename $dir_name)
account_id=`aws sts get-caller-identity --output text --query 'Account'`
docker --version
docker build -t $image_name $dir_name
aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin $account_id.dkr.ecr.eu-west-2.amazonaws.com
if [ $(aws ecr describe-repositories --repository-names $image_name --region eu-west-2) | grep -q RepositoryNotFoundException]; then
    if echo ${output} | grep -q RepositoryNotFoundException; then
        aws ecr create-repository --repository-name $image_name --region eu-west-2 --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
    else
        echo "Repository already exists" 
    fi
else
    echo "repo"
fi


exit


