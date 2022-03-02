#!/bim/bash

set -e
docker ps

source_path=$(which $0)

dir_name=$(dirname $source_path)
image_name=$(basename $dir_name)
account_id=`aws sts get-caller-identity --output text --query 'Account'`

aws lambda update-function-code --function-name $image_name --image-uri $account_id.dkr.ecr.eu-west-2.amazonaws.com/$image_name:latest