# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from fastapi import FastAPI

from api.imports import *
from tasks.Import import ImportAnalysis, RealImport

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


# In a development environment, dump the API definition at each run
def dump_openapi():
    import sys
    if "--reload" not in sys.argv:
        return  # It's not dev
    import json
    from pathlib import Path
    dest: Path = Path("..") / "openapi.json"
    with dest.open("w") as fd:
        json_def = json.dumps(app.openapi(),
                              ensure_ascii=False,
                              allow_nan=False,
                              indent=None,
                              separators=(",", ":"))
        fd.write(json_def)


dump_openapi()
