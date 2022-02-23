#!/bin/bash
# 33:33 is www-data
# Add -i for having a console:
#docker run -it --rm \
echo '*************************** VERSION HEAD ****************************'
#docker run -d --restart unless-stopped \
docker run --rm --gpus all \
-u 1000:1000 --name ecotaxagpuback  \
--mount type=bind,source=${PWD}/../py/config.ini,target=/config.ini  \
--mount type=bind,source=/vieux,target=/vieux  \
--mount type=bind,source=/var/run/postgresql,target=/var/run/postgresql  \
--mount type=bind,source=/home/laurent/Devs/ecotaxa/SrvFics/,target=/home/laurent/Devs/ecotaxa/SrvFics \
--mount type=bind,source=/home/laurent/Devs/ecotaxa/models,target=/home/laurent/Devs/ecotaxa/models \
--mount type=bind,source=/home/laurent/Devs/from_Lab/ecotaxa_master/temptask,target=/home/laurent/Devs/from_Lab/ecotaxa_master/temptask \
grololo06/ecotaxagpuback
# Add this in the end to skip the init
#bash

