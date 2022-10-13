#!/usr/bin/env bash
docker_image_name=tre-bagit-to-dri-sip
docker_image_tag=0.0.8
# shellcheck disable=SC2034  # var imported elsewhere
docker_image="${docker_image_name}":"${docker_image_tag}"
# shellcheck disable=SC2034  # var imported elsewhere
lib_build_list=('s3_lib')
tre_event_lib_build_tag=0.0.7-alpha
