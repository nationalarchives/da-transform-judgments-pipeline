#!/usr/bin/env bash
docker_image_name=tre-validate-bagit-files
docker_image_tag=2.0.1
# shellcheck disable=SC2034  # var imported elsewhere
docker_image="${docker_image_name}":"${docker_image_tag}"
# shellcheck disable=SC2034  # var imported elsewhere
lib_build_list=('s3_lib' 'lib/tre_lib')
