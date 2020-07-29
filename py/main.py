# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Based on https://fastapi.tiangolo.com/release-notes/
#
import sys
import traceback
from typing import Any, Tuple, Union

from fastapi import FastAPI, Response, status, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature, TimestampSigner
from uvicorn.middleware.debug import PlainTextResponse

from api.exports import EMODNetExportReq, EMODNetExportRsp
from api.imports import *
from link import read_config
from tasks.Import import ImportAnalysis, RealImport
from tasks.SimpleImport import SimpleImport
from tasks.WoRMSFinder import WoRMSFinder
from tasks.export.EMODnet import EMODNetExport
from tech.StatusSce import StatusService

# TODO: A nicer API doc, see https://github.com/tiangolo/fastapi/issues/1140

app = FastAPI(title="EcoTaxa",
              version="0.0.1")

secured_scheme = HTTPBearer()

# Read from legacy app config
SECRET_KEY = read_config()['SECRET_KEY'][1:-1]
# Hardcoded in Flask
SALT = b"cookie-session"

serializer = URLSafeTimedSerializer(secret_key=SECRET_KEY, salt=SALT,
                                    signer=TimestampSigner, signer_kwargs={'key_derivation': 'hmac'})
max_age = 2678400  # max token age, 31 days


async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(secured_scheme)) -> int:
    """
        Extract current user from auth string.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if creds.scheme != 'Bearer':
            raise credentials_exception
        payload = serializer.loads(creds.credentials, max_age=max_age)
        try:
            ret: int = int(payload["user_id"])
        except (KeyError, ValueError):
            raise credentials_exception
    except (SignatureExpired, BadSignature):
        raise credentials_exception
    if ret < 0:
        raise credentials_exception
    return ret


@app.get("/taxon/resolve/{our_id}", status_code=status.HTTP_200_OK)
async def api_resolve_taxon(our_id: int, response: Response, t=None) -> Union[
    PlainTextResponse, Tuple]:
    """
        Resolve in WoRMs the given taxon.
    """
    sce = WoRMSFinder(our_id)
    ok, ours, theirs = await sce.run()
    if ok < 0:
        response.status_code = status.HTTP_404_NOT_FOUND
    if t:
        data = "id:%s\nours : %s\ntheir : %s\n" % (our_id, ours, theirs)
        response.body = data
        return Response(data, media_type="text/plain", status_code=status.HTTP_200_OK)
    else:
        ret = ok, ours, theirs
        return ret


@app.post("/import_prep/{project_id}", response_model=ImportPrepRsp)
def api_import(project_id: int, params: ImportPrepReq, current_user: int = Depends(get_current_user)):
    """
        Prepare/validate the import of an EcoTaxa archive or directory.
    """
    sce = ImportAnalysis(project_id, params)
    return sce.run()


@app.post("/import_real/{project_id}", response_model=ImportRealRsp)
def api_import(project_id: int, params: ImportRealReq, current_user: int = Depends(get_current_user)):
    """
        Import an EcoTaxa archive or directory.
    """
    sce = RealImport(project_id, params)
    return sce.run()


@app.post("/simple_import/{project_id}", response_model=SimpleImportRsp)
def api_import(project_id: int, params: SimpleImportReq, current_user: int = Depends(get_current_user)):
    """
        Import images only, with same metadata for all.
    """
    sce = SimpleImport(project_id, params)
    return sce.run()


@app.post("/export/emodnet", response_model=EMODNetExportRsp)
def api_export_emodnet(params: EMODNetExportReq, current_user: int = Depends(get_current_user)):
    """
        Export in EMODnet format, @see https://www.emodnet-ingestion.eu/
        Produces a DwC-A archive into a temporary directory, ready for download.
        https://python-dwca-reader.readthedocs.io/en/latest/index.html
    """
    sce = EMODNetExport(params)
    return sce.run()


@app.get("/status")
def api_status() -> Response:
    """
        Report the status, mainly used for verifying that the server is up.
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
    status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    tb = traceback.format_exception(tpe, val, tbk)
    our_stack_ndx = 0
    # Remove all until our code
    for ndx, a_line in enumerate(tb):
        if a_line.find("main.py") != -1:
            our_stack_ndx = ndx
            break
    data = "\n----------- BACK-END -------------\n" + "".join(tb[our_stack_ndx:])
    return PlainTextResponse(data, status_code=status_code)


app.add_exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR, internal_server_error_handler)


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
