#!/usr/bin/env bash
docker_image_name=tre-forward
docker_image_tag=2.0.3
# shellcheck disable=SC2034  # var imported elsewhere
docker_image="${docker_image_name}":"${docker_image_tag}"
