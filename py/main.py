# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from fastapi import FastAPI

from api.imports import *
from tasks.Import import ImportAnalysis, RealImport

# TODO: A nicer API doc, see https://github.com/tiangolo/fastapi/issues/1140

app = FastAPI()
app.openapi_prefix = "/api"
app.title = "EcoTaxa"


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
