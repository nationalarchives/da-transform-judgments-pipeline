#!/usr/bin/env bash
set -e

. ./vars.sh
ecr_repository_name="lambda_functions/${docker_image_name}"
printf 'Creating ECR repository "%s"\n' "${ecr_repository_name}"

aws ecr create-repository \
    --repository-name "${ecr_repository_name}" \
    --image-scanning-configuration \
    scanOnPush=true
