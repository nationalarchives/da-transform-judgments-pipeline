#!/usr/bin/env bash
set -e
. vars.sh

if [ $# -ne 1 ]; then
  printf 'ERROR: Usage: repository_uri\n'
  exit 1
fi

repository_uri="$1"

# Tag built image with both build version and "latest", for push to ECR
tag_version="${repository_uri}:${docker_image_tag}"
tag_latest="${repository_uri}:latest"

printf 'Tagging "%s" as "%s"\n' "${docker_image}" "${tag_version}"
docker tag "${docker_image}" "${tag_version}"
printf 'Tagging "%s" as "%s"\n' "${docker_image}" "${tag_latest}"
docker tag "${docker_image}" "${tag_latest}"
