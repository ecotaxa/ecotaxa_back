#!/bin/bash
VERSION=3.0.0
# In case of doubt on the image sanity or if you have time, uncomment below
#NO_CACHE=--no-cache
# In case you need full output of commands, e.g. for ensuring python packages version, uncomment below
#export BUILDKIT_PROGRESS=plain
# Preliminary, log using ecotaxa docker account
#docker login -u ecotaxa
# Copy all sources
(cd .. && git status py --porcelain | grep "??" | sed -e "s/.. py\///g" > docker/not_in_git.lst)
rsync -avr --delete --exclude-from=not_to_copy.lst --exclude-from=not_in_git.lst ../py/ py/
mkdir -p docker/prod_image
rsync prod_image/start.sh  docker/prod_image/
# Build
docker build $NO_CACHE -t ecotaxa/ecotaxa_back -f prod_image/Dockerfile .
# Publish
docker tag ecotaxa/ecotaxa_back:latest ecotaxa/ecotaxa_back:$VERSION
docker push ecotaxa/ecotaxa_back:$VERSION
docker push ecotaxa/ecotaxa_back:latest
