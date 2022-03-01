#!/bin/bash
# 33:33 is www-data
# Add -i for having a console:
#docker run -it --rm \
echo '*************************** VERSION HEAD ****************************'
#docker run -d --restart unless-stopped \
docker run --security-opt seccomp=unconfined \
-u 1000:1000 -p 8000:8000 --name ecotaxaback  \
-e "WEB_CONCURRENCY=2" \
--mount type=bind,source=${PWD}/../py/config.ini,target=/config.ini  \
--mount type=bind,source=/vieux,target=/vieux  \
--mount type=bind,source=/var/run/postgresql,target=/var/run/postgresql  \
--mount type=bind,source=/home/laurent/Devs/ecotaxa/SrvFics/,target=/home/laurent/Devs/ecotaxa/SrvFics \
grololo06/ecotaxaback
# Add this in the end to skip the init
#bash

