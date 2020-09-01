# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Based on https://fastapi.tiangolo.com/
#
from typing import Union, Tuple

from fastapi import FastAPI, Response, status, Depends
from fastapi_utils.timing import add_timing_middleware

from API_models.crud import *
from API_models.exports import EMODNetExportReq, EMODNetExportRsp
from API_models.imports import *
from API_models.merge import MergeRsp
from API_models.subset import SubsetReq, SubsetRsp
from API_operations.CRUD.Projects import ProjectsService, ProjectSearchResult
from API_operations.CRUD.Users import UserService
from API_operations.Consistency import ProjectConsistencyChecker
from API_operations.JsonDumper import JsonDumper
from API_operations.Merge import MergeService
from API_operations.Status import StatusService
from API_operations.Subset import SubsetService
from API_operations.exports.EMODnet import EMODNetExport
from API_operations.helpers.Service import Service
from API_operations.imports.Import import ImportAnalysis, RealImport
from API_operations.imports.SimpleImport import SimpleImport
from helpers.DynamicLogs import get_logger
from helpers.fastApiUtils import internal_server_error_handler, dump_openapi, get_current_user, RightsThrower
from helpers.starlette import PlainTextResponse
# noinspection PyPackageRequirements
from providers.WoRMS import WoRMSFinder

logger = get_logger(__name__)

# TODO: A nicer API doc, see https://github.com/tiangolo/fastapi/issues/1140

app = FastAPI(title="EcoTaxa",
              version="0.0.2",
              # openapi URL as seen from navigator
              openapi_url="/api/openapi.json",
              # root_path="/API_models"
              )

# Instrument a bit
add_timing_middleware(app, record=logger.info, prefix="app", exclude="untimed")


# noinspection PyUnusedLocal
@app.post("/login", tags=['authentification'])
async def login(username: str, password: str) -> str:
    """
        Just for description. The _real_ login is done in legacy code via flask.
    """
    return "Do not use. Use home site /login page instead."


# TODO: when python 3.7+, we can have pydantic generics and remove the ignore below
@app.get("/users", tags=['users'], response_model=List[UserModel])  # type:ignore
def get_users(current_user: int = Depends(get_current_user)):
    """
        Return the list of users.
    """
    sce = UserService()
    return sce.list(current_user)


# TODO: when python 3.7+, we can have pydantic generics and remove the ignore below
@app.get("/users/me", tags=['users'], response_model=UserModel)  # type:ignore
def show_current_user(current_user: int = Depends(get_current_user)):
    """
        Return currently authenticated user.
    """
    sce = UserService()
    return sce.search_by_id(current_user, current_user)


# TODO: when python 3.7+, we can have pydantic generics and remove the ignore below
@app.get("/users/search", tags=['users'], response_model=List[UserModel])  # type:ignore
def search_user(current_user: int = Depends(get_current_user),
                by_name: Optional[str] = None):
    """
        Search users using various criteria, search is case insensitive and might contain % chars.
    """
    sce = UserService()
    ret = sce.search(current_user, by_name)
    return ret


@app.get("/projects/search", tags=['projects'], response_model=List[ProjectSearchResult])
def search_projects(current_user: int = Depends(get_current_user),
                    also_others: bool = False,
                    for_managing: bool = False,
                    title_filter: str = '',
                    instrument_filter: str = '',
                    filter_subset: bool = False):
    """
        Return projects summary for current user.
        - @param also_others: Allows to return projects for which given user has no right
        - @param for_managing: Allows to return project that can be written to (including erased) by the given user
        - @param title_filter: Use this pattern for matching returned projects names
        - @param instrument_filter: Only return projects where this instrument was used
        - @param filter_subset: Only return projects having 'subset' in their names
    """
    sce = ProjectsService()
    ret = sce.search(current_user_id=current_user, also_others=also_others, for_managing=for_managing,
                     title_filter=title_filter, instrument_filter=instrument_filter, filter_subset=filter_subset)
    return ret


@app.post("/projects/create", tags=['projects'], response_model=int)
def create_project(params: CreateProjectReq, current_user: int = Depends(get_current_user)):
    """
        Create an empty project with only a title, and return its number.
        The project will be managed by current user.
        The user has to be app administrator or project creator.
    """
    sce = ProjectsService()
    with RightsThrower():
        ret = sce.create(current_user, params)
    return ret


@app.post("/projects/{project_id}/subset", tags=['projects'], response_model=SubsetRsp)
def project_subset(project_id: int, params: SubsetReq, current_user: int = Depends(get_current_user)):
    """
        Subset a project into another one.
    """
    sce = SubsetService(project_id, params)
    with RightsThrower():
        return sce.run(current_user)


@app.post("/projects/{project_id}/query", tags=['projects'], include_in_schema=False, response_model=SubsetRsp)
def project_query(project_id: int, filters: ProjectFiltersModel, current_user: int = Depends(get_current_user)):
    """
        Query the project.
    """
    # TODO: Use a StreamingResponse to avoid buffering
    sce = JsonDumper(current_user, project_id, filters)
    # TODO: Finish. lol.
    import sys
    return sce.run(sys.stdout)


@app.post("/projects/{project_id}/merge", tags=['projects'], response_model=MergeRsp)
def project_merge(project_id: int, source_project_id: int, dry_run: bool,
                  current_user: int = Depends(get_current_user)) -> MergeRsp:
    """
        Merge another project into this one. It's more a phagocytosis than a merge, as the source will see
        all its objects gone and will be erased.
        - param `dry_run`: If set, then only a diagnostic of doability will be done.
    """
    sce = MergeService(project_id, source_project_id, dry_run)
    with RightsThrower():
        return sce.run(current_user)


@app.get("/projects/{project_id}/check", tags=['projects'])
def project_check(project_id: int, current_user: int = Depends(get_current_user)):
    """
        Check consistency of a project.
    """
    sce = ProjectConsistencyChecker(project_id)
    with RightsThrower():
        return sce.run(current_user)


@app.post("/import_prep/{project_id}", tags=['projects'], response_model=ImportPrepRsp)
def import_preparation(project_id: int, params: ImportPrepReq, current_user: int = Depends(get_current_user)):
    """
        Prepare/validate the import of an EcoTaxa archive or directory.
    """
    sce = ImportAnalysis(project_id, params)
    with RightsThrower():
        return sce.run(current_user)


@app.post("/import_real/{project_id}", tags=['projects'], response_model=ImportRealRsp)
def real_import(project_id: int, params: ImportRealReq, current_user: int = Depends(get_current_user)):
    """
        Import an EcoTaxa archive or directory.
    """
    sce = RealImport(project_id, params)
    with RightsThrower():
        return sce.run(current_user)


@app.post("/simple_import/{project_id}", tags=['projects'], response_model=SimpleImportRsp)
def simple_import(project_id: int, params: SimpleImportReq, current_user: int = Depends(get_current_user)):
    """
        Import images only, with same metadata for all.
    """
    sce = SimpleImport(project_id, params)
    with RightsThrower():
        return sce.run(current_user)


@app.post("/export/emodnet", tags=['WIP'], include_in_schema=False, response_model=EMODNetExportRsp)
def emodnet_format_export(params: EMODNetExportReq, current_user: int = Depends(get_current_user)):
    """
        Export in EMODnet format, @see https://www.emodnet-ingestion.eu/
        Produces a DwC-A archive into a temporary directory, ready for download.
        https://python-dwca-reader.readthedocs.io/en/latest/index.html
    """
    sce = EMODNetExport(params)
    with RightsThrower():
        return sce.run(current_user)


@app.get("/taxon/resolve/{our_id}", tags=['WIP'], include_in_schema=False, status_code=status.HTTP_200_OK)
async def resolve_taxon(our_id: int, response: Response, text_response: bool = False,
                        _current_user: int = Depends(get_current_user)) -> Union[
    PlainTextResponse, Tuple]:
    """
        Resolve in WoRMs the given taxon.
        :param text_response: If set, response will be plain text. If not, JSON.
    """
    sce = WoRMSFinder(Service().session, our_id)
    ok, ours, theirs = await sce.run()
    if ok < 0:
        response.status_code = status.HTTP_404_NOT_FOUND
    if text_response:
        data = "id:%s\nours : %s\ntheir : %s\n" % (our_id, ours, theirs)
        response.body = bytes(data, 'utf-8')
        return PlainTextResponse(data, status_code=status.HTTP_200_OK)
    else:
        ret = ok, ours, theirs
        return ret


@app.get("/status", tags=['WIP'])
def system_status(_current_user: int = Depends(get_current_user)) -> Response:
    """
        Report the status, mainly used for verifying that the server is up.
    """
    sce = StatusService()
    return Response(sce.run(), media_type="text/plain")


# @app.get("/loadtest", tags=['WIP'], include_in_schema=False)
# def load_test() -> Response:
#     """
#         Simulate load with various response time. The Service() gets a session from the DB pool.
#         See if we just wait or fail to server:
#         httperf --server=localhost --port=8000 --uri=/loadtest --num-conns=1000 --num-calls=10
#     """
#     sce = StatusService()
#     import time
#     time.sleep(random()/10)
#     return Response(sce.run(), media_type="text/plain")


app.add_exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR, internal_server_error_handler)

dump_openapi(app, __file__)
