#!/usr/bin/env bash
docker_image_name=tre-step-function-trigger
docker_image_tag=0.0.9
# shellcheck disable=SC2034  # var imported elsewhere
docker_image="${docker_image_name}":"${docker_image_tag}"
