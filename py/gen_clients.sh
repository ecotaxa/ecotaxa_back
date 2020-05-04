#!/bin/bash
#
# Generate client stubs for python
#
# !!! This script needs the development server of ecotaxa_back running !!!
#
docker run --rm --network="host" -v ${PWD}/..:/back openapitools/openapi-generator-cli generate \
 -i http://localhost:8000/openapi.json -g python \
 --additional-properties=generateSourceCodeOnly=true,packageName=ecotaxa_api \
 -o /back/client/py
 # Generated files belong to root, fix it.
 sudo chown -R $(id -u):$(id -g) ../client