#!/usr/bin/env bash
docker_image_name=tre-sqs-sf-trigger
docker_image_tag=2.0.4
# shellcheck disable=SC2034  # var imported elsewhere
docker_image="${docker_image_name}":"${docker_image_tag}"
