#
# A python generator from OpenAPI spec.
#
# Heavily patched version of https://pypi.org/project/openapi-python-client/
#
from shutil import rmtree

import sys
sys.path.extend(["openapi-python-client-0.5.3-patched",
                 "openapi-python-client-0.5.3-patched/openapi_python_client"])

from openapi_python_client.cli import app

rmtree("eco-taxa-client", ignore_errors=True)
app(["generate", "--path", "../../../openapi.json"])
