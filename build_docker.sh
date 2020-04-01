#!/bin/bash
#
# This command needs to be launched from here, as the docker needs to access project files
#
# The docker image is referenced in GitHub QA actions
#
docker build -t grololo06/ecotaxa -f docker/test_image/Dockerfile
# once built:
# docker push grololo06/ecotaxa:latest
# needing before:
# docker login