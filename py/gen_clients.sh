#!/bin/bash
#
# Generate client stubs for python
#
# !!! This script needs the development server of ecotaxa_back running !!!
#
docker run --rm --network="host" -v ${PWD}/../../ecotaxa_client:/client openapitools/openapi-generator-cli generate \
 -i https://raw.githubusercontent.com/ecotaxa/ecotaxa_back/master/openapi.json -g python \
 --additional-properties=generateSourceCodeOnly=true,packageName=ecotaxa_cli_py \
 -o /client
 # Generated files belong to root, fix it.
 sudo chown -R $(id -u):$(id -g) ../../ecotaxa_client