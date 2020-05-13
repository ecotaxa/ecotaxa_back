#!/bin/bash
#
# Due to Docker fs, we need to copy all sources
#
rsync -avr --delete --exclude-from=not_to_copy.lst ../py/ py/
cp ../link.ini .
docker build -t grololo06/ecotaxaback -f prod_image/Dockerfile .
# once built:
#docker images
#docker tag 933912b1ecd2 grololo06/ecotaxaback:2.3
#docker push grololo06/ecotaxaback:2.3
# needing before:
# docker login
