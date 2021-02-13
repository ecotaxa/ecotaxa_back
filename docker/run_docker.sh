#!/bin/bash
# 33:33 is www-data
# Add -i for having a console:
#docker run -it --rm \
echo '*************************** VERSION HEAD ****************************'
docker run -d --restart unless-stopped \
-u 33:33 -p 8000:8000 --name ecotaxaback  \
--mount type=bind,source=${PWD}/../../ecotaxa_master,target=/ecotaxa_master  \
--mount type=bind,source=/var/run/postgresql,target=/var/run/postgresql  \
--mount type=bind,source=/home/laurent/Devs/ecotaxa/SrvFics/,target=/plankton_rw \
grololo06/ecotaxaback
# Add this in the end to skip the init
#bash

