#!/bin/bash
#
# Due to Docker fs, we need to copy all sources
#
rsync -avr --delete --exclude-from=not_to_copy.lst ../py/ py/
cp ../link.ini .
docker build -t grololo06/ecotaxaback -f prod_image/Dockerfile .
# once built:
# docker push grololo06/ecotaxaback:latest
# needing before:
# docker login
