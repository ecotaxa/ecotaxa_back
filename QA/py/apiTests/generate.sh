#
# Generate client stubs.
# Depends on openapi-generator-cli==4.3.1
#
openapi-generator generate  -i ../../../openapi.json -g python  --minimal-update  --additional-properties=generateSourceCodeOnly=true,packageName=ecotaxa_cli_py  -o ..
