# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import sys
import traceback
from typing import Any

from fastapi import FastAPI, Response
from uvicorn.middleware.debug import PlainTextResponse

from api.imports import *
from tasks.Import import ImportAnalysis, RealImport
from tech.StatusSce import StatusService

# TODO: A nicer API doc, see https://github.com/tiangolo/fastapi/issues/1140

app = FastAPI(title="EcoTaxa",
              version="0.0.1")


@app.post("/import_prep/{project_id}", response_model=ImportPrepRsp)
def api_import(project_id: int, params: ImportPrepReq):
    """
        Prepare/validate the import of an EcoTaxa archive or directory.
    """
    sce = ImportAnalysis(project_id, params)
    return sce.run()


@app.post("/import_real/{project_id}", response_model=ImportRealRsp)
def api_import(project_id: int, params: ImportRealReq):
    """
        Import an EcoTaxa archive or directory.
    """
    sce = RealImport(project_id, params)
    return sce.run()

@app.get("/status")
def api_status() -> Response:
    """
        Import an EcoTaxa archive or directory.
    """
    sce = StatusService()
    return Response(sce.run(), media_type="text/plain")

async def internal_server_error_handler(_request: Any, exc: Exception) -> PlainTextResponse:
    """
        Override internal error handler, so that we don't have to look at logs on server side in case of problem.
    :param _request:
    :param exc: The exception caught.
    :return:
    """
    tpe, val, tbk = sys.exc_info()
    status_code = getattr(exc, "status_code", 500)
    tb = traceback.format_exception(tpe, val, tbk)
    our_stack_ndx = 0
    # Remove all until our code
    for ndx, a_line in enumerate(tb):
        if a_line.find("main.py") != -1:
            our_stack_ndx = ndx
            break
    data = "\n----------- BACK-END -------------\n" + "".join(tb[our_stack_ndx:])
    return PlainTextResponse(data, status_code=status_code)


app.add_exception_handler(500, internal_server_error_handler)


# In a development environment, dump the API definition at each run
def dump_openapi():
    import sys
    if "--reload" not in sys.argv:
        return  # It's not dev
    import json
    from pathlib import Path
    json_def = json.dumps(app.openapi(),
                          ensure_ascii=False,
                          allow_nan=False,
                          indent=None,
                          separators=(",", ":"))
    # Copy here for Git commit but also into another dev tree
    dests = [Path("../openapi.json"), Path("../../ecotaxa_master/to_back/openapi.json")]
    for dest in dests:
        with dest.open("w") as fd:
            fd.write(json_def)


dump_openapi()
