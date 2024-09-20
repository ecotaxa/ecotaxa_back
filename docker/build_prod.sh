#!/bin/bash
VERSION=2.7.6.3
# In case of doubt on the image sanity or if you have time, uncomment below
#NO_CACHE=--no-cache
# Preliminary, log using ecotaxa docker account
#docker login -u ecotaxa
# Copy all sources
(cd .. && git status py --porcelain | grep "??" | sed -e "s/.. py\///g" > docker/not_in_git.lst)
rsync -avr --delete --exclude-from=not_to_copy.lst --exclude-from=not_in_git.lst ../py/ py/
# Build
docker build $NO_CACHE -t ecotaxa/ecotaxa_back -f prod_image/Dockerfile .
docker build $NO_CACHE -t ecotaxa/ecotaxa_gpu_back -f gpu_prod_image/Dockerfile .
# Publish
docker tag ecotaxa/ecotaxa_back:latest ecotaxa/ecotaxa_back:$VERSION
docker push ecotaxa/ecotaxa_back:$VERSION
docker push ecotaxa/ecotaxa_back:latest
# GPU
docker tag ecotaxa/ecotaxa_gpu_back:latest ecotaxa/ecotaxa_gpu_back:$VERSION
# The push takes ages because the image comes from official Nvidia one which is 1.7G in size
docker push ecotaxa/ecotaxa_gpu_back:$VERSION
docker push ecotaxa/ecotaxa_gpu_back:latest

