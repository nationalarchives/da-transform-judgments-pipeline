#!/usr/bin/env bash
set -e

. vars.sh
aws ecr create-repository \
    --repository-name "lambda_functions/${docker_image_name}" \
    --image-scanning-configuration \
    scanOnPush=true
