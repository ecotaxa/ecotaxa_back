#!/bin/bash
# 33:33 is www-data
# Add -i for having a console:
#docker run -it --rm \
echo '*************************** VERSION HEAD ****************************'
#docker run -d --restart unless-stopped \
docker run --rm --gpus all --security-opt seccomp=unconfined \
-u 1000:1000 --name ecotaxagpuback  \
--mount type=bind,source=${PWD}/../py/config.ini,target=/config.ini  \
--mount type=bind,source=${PWD}/../vault,target=/vault  \
--mount type=bind,source=${PWD}/../temptask,target=/temptask \
--mount type=bind,source=${PWD}/../srv_fics,target=/srv_fics \
--mount type=bind,source=${PWD}/../ftp,target=/ftp \
--mount type=bind,source=/home/laurent/Devs/ecotaxa/models,target=/home/laurent/Devs/ecotaxa/models \
ecotaxa/ecotaxa_gpu_back:2.6.2
# Add this in the end to skip the init
#bash

