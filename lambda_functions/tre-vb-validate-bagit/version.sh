#!/usr/bin/env bash
docker_image_name=tre-vb-validate-bagit
docker_image_tag=2.0.4
# shellcheck disable=SC2034  # var imported elsewhere
docker_image="${docker_image_name}":"${docker_image_tag}"
# shellcheck disable=SC2034  # var imported elsewhere
lib_build_list=('s3_lib')
# shellcheck disable=SC2034  # var imported elsewhere
tre_event_lib_build_tag=0.0.3-alpha
