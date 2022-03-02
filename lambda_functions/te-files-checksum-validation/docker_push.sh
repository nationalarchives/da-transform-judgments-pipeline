#!/usr/bin/env bash
set -e
. vars.sh

if [ $# -ne 1 ]; then
  printf 'ERROR: Usage: repository_uri\n'
  exit 1
fi

repository_uri="$1"
tag_version="${repository_uri}:${docker_image_tag}"
tag_latest="${repository_uri}:latest"
printf 'Pushing "%s"\n' "${tag_version}"
docker push "${tag_version}"
printf 'Pushing "%s"\n' "${tag_latest}"
docker push "${tag_latest}"
