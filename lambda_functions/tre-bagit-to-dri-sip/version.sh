#!/usr/bin/env bash
docker_image_name=tre_bagit_to_dri_sip
docker_image_tag=0.0.1
# shellcheck disable=SC2034  # var imported elsewhere
docker_image="${docker_image_name}":"${docker_image_tag}"
