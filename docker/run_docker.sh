#!/bin/bash
# 33:33 is www-data
# Add -i for having a console:
#docker run -it --rm \
echo '*************************** VERSION HEAD ****************************'
#docker run -d --restart unless-stopped \
docker run --security-opt seccomp=unconfined \
-u 1000:1000 --network econet -p 8000:8000 --name ecotaxaback  \
-e "WEB_CONCURRENCY=2" \
-v ${PWD}/../py/config.ini:/config.ini  \
-v /vieux:/vieux  \
-v /home/laurent/Devs/ecotaxa/SrvFics/:/home/laurent/Devs/ecotaxa/SrvFics \
ecotaxa/ecotaxa_back
# Add this in the end to skip the init
#bash

