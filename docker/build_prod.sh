#!/bin/bash
#
# Due to Docker fs, we need to copy all sources
#
rsync -avr --delete --exclude-from=not_to_copy.lst ../py/ py/
cp ../link.ini .
docker build -t grololo06/ecotaxaback -f prod_image/Dockerfile .
# once built:
#   docker tag grololo06/ecotaxaback:latest grololo06/ecotaxaback:2.3
#   docker push grololo06/ecotaxaback:2.3
# needing before:
#   docker login
