# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Based on https://fastapi.tiangolo.com/
#
import os
from logging import INFO
from typing import Union, Tuple

from fastapi import FastAPI, Request, Response, status, Depends, HTTPException, UploadFile, File, Query, Form
from fastapi.logger import logger as fastapi_logger
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi_utils.timing import add_timing_middleware

from API_models.constants import Constants
from API_models.crud import *
from API_models.exports import EMODnetExportRsp, ExportRsp, ExportReq
from API_models.filesystem import DirectoryModel
from API_models.helpers.Introspect import plain_columns
from API_models.imports import *
from API_models.login import LoginReq
from API_models.merge import MergeRsp
from API_models.objects import ObjectSetQueryRsp, ObjectSetRevertToHistoryRsp, ClassifyReq, ObjectModel, \
    ObjectHeaderModel, HistoricalClassificationModel, ObjectSetSummaryRsp, ClassifyAutoReq
from API_models.subset import SubsetReq, SubsetRsp
from API_models.taxonomy import TaxaSearchRsp, TaxonModel, TaxonomyTreeStatus
from API_operations.CRUD.Collections import CollectionsService
from API_operations.CRUD.Constants import ConstantsService
from API_operations.CRUD.Instruments import InstrumentsService
from API_operations.CRUD.Jobs import JobCRUDService
from API_operations.CRUD.Object import ObjectService
from API_operations.CRUD.ObjectParents import SamplesService, AcquisitionsService, ProcessesService
from API_operations.CRUD.Projects import ProjectsService
from API_operations.CRUD.Users import UserService
from API_operations.Consistency import ProjectConsistencyChecker
from API_operations.DBSyncService import DBSyncService
from API_operations.JsonDumper import JsonDumper
from API_operations.Merge import MergeService
from API_operations.ObjectManager import ObjectManager
from API_operations.Stats import ProjectStatsFetcher
from API_operations.Status import StatusService
from API_operations.Subset import SubsetServiceOnProject
from API_operations.TaxoManager import TaxonomyChangeService, CentralTaxonomyService
from API_operations.TaxonomyService import TaxonomyService
from API_operations.UserFolder import UserFolderService, CommonFolderService
from API_operations.admin.ImageManager import ImageManagerService
from API_operations.admin.NightlyJob import NightlyJobService
from API_operations.exports.EMODnet import EMODnetExport
from API_operations.exports.ForProject import ProjectExport
from API_operations.imports.Import import FileImport
from API_operations.imports.SimpleImport import SimpleImport
from BG_operations.JobScheduler import JobScheduler
from BO.Acquisition import AcquisitionBO
from BO.Classification import HistoricalClassification
from BO.Job import JobBO
from BO.Object import ObjectBO
from BO.ObjectSet import ObjectIDListT
from BO.Preferences import Preferences
from BO.Process import ProcessBO
from BO.Project import ProjectBO, ProjectTaxoStats, ProjectUserStats
from BO.Rights import RightsBO
from BO.Sample import SampleBO
from BO.Taxonomy import TaxonBO
from DB import ProjectPrivilege
from DB.Project import ProjectTaxoStat
from helpers.Asyncio import async_bg_run, log_streamer
from helpers.DynamicLogs import get_logger
from helpers.fastApiUtils import internal_server_error_handler, dump_openapi, get_current_user, RightsThrower, \
    get_optional_current_user, MyORJSONResponse, ValidityThrower
from helpers.login import LoginService
from helpers.pydantic import sort_and_prune

# from fastapi.middleware.gzip import GZipMiddleware

logger = get_logger(__name__)
# TODO: A nicer API doc, see https://github.com/tiangolo/fastapi/issues/1140

fastapi_logger.setLevel(INFO)

app = FastAPI(title="EcoTaxa",
              version="0.0.16",
              # openapi URL as seen from navigator, this is included when /docs is required
              # which serves swagger-ui JS app. Stay in /api sub-path.
              openapi_url="/api/openapi.json",
              servers=[
                  {"url": "/api", "description": "External access"},
                  {"url": "/", "description": "Local access"},
              ],
              default_response_class=MyORJSONResponse
              # For later: Root path is in fact _removed_ from incoming requests, so not relevant here
              )

# Instrument a bit
add_timing_middleware(app, record=logger.info, prefix="app", exclude="untimed")

# Optimize large responses
# app.add_middleware(GZipMiddleware, minimum_size=1024)

# HTML stuff
# app.mount("/styles", StaticFiles(directory="pages/styles"), name="styles")
templates = Jinja2Templates(directory=os.path.dirname(__file__) + "/pages/templates")
# Below is useless if proxied by legacy app
CDNs = " ".join(["cdn.datatables.net"])
CRSF_header = {
    'Content-Security-Policy': "default-src 'self' 'unsafe-inline' 'unsafe-eval' "
                               f"blob: data: {CDNs};frame-ancestors 'self';form-action 'self';"
}

# Establish second routes via /api to same app
app.mount("/api", app)


# noinspection PyUnusedLocal
@app.post("/login", tags=['authentification'])
async def login(params: LoginReq) -> str:
    """
        Login barrier. If successful, the login will return a JWT which will have to be used
        in Bearer authentication scheme for subsequent calls.

        -`username`: User *email* which was used during registration

        -`password`: User password
    """
    with LoginService() as sce:
        with RightsThrower():
            return sce.validate_login(params.username, params.password)


@app.get("/users", tags=['users'], response_model=List[UserModel])
def get_users(current_user: int = Depends(get_current_user)):
    """
        Return the list of users. For admins only.
    """
    with UserService() as sce:
        return sce.list(current_user)


@app.get("/users/me", tags=['users'], response_model=UserModelWithRights)
def show_current_user(current_user: int = Depends(get_current_user)):
    """
        Return currently authenticated user. On top of DB fields, 'can_do' lists the allowed system-wide actions.
    """
    with UserService() as sce:
        ret = sce.search_by_id(current_user, current_user)
        assert ret is not None
        # noinspection PyTypeHints
        ret.can_do = RightsBO.allowed_actions(ret)  # type:ignore
        # noinspection PyTypeHints
        ret.last_used_projects = Preferences(ret).recent_projects(session=sce.session)  # type:ignore
        return ret


@app.get("/users/my_preferences/{project_id}", tags=['users'], response_model=str)
def get_current_user_prefs(project_id: int,
                           key: str,
                           current_user: int = Depends(get_current_user)) -> str:
    """
        Return one preference, for project and currently authenticated user.
    """
    with UserService() as sce:
        return sce.get_preferences_per_project(current_user, project_id, key)


@app.put("/users/my_preferences/{project_id}", tags=['users'])
def set_current_user_prefs(project_id: int,
                           key: str,
                           value: str,
                           current_user: int = Depends(get_current_user)):
    """
        Set one preference, for project and currently authenticated user.
        -`key`: The preference key
        -`value`: The value to set this preference to.
    """
    with UserService() as sce:
        return sce.set_preferences_per_project(current_user, project_id, key, value)


@app.get("/users/search", tags=['users'], response_model=List[UserModel])
def search_user(current_user: int = Depends(get_current_user),
                by_name: Optional[str] = None):
    """
        Search users using various criteria, search is case insensitive and might contain % chars.
    """
    with UserService() as sce:
        ret = sce.search(current_user, by_name)
    return ret


@app.get("/users/{user_id}", tags=['users'], response_model=UserModel)
def get_user(user_id: int,
             current_user: int = Depends(get_current_user)):
    """
        Return a single user by its id.
    """
    with UserService() as sce:
        ret = sce.search_by_id(current_user, user_id)
    if ret is None:
        raise HTTPException(status_code=404, detail="User not found")
    return ret


# ######################## END OF USER

@app.post("/collections/create", tags=['collections'])
def create_collection(params: CreateCollectionReq,
                      current_user: int = Depends(get_current_user)) -> Union[int, str]:
    """
        Create a collection with at least one project inside.

        *Currently only for admins*
    """
    with CollectionsService() as sce:
        with RightsThrower():
            ret = sce.create(current_user, params)
    if isinstance(ret, str):
        raise HTTPException(status_code=404, detail=ret)
    # TODO: Mettre les syncs dans les services, moins dégeu
    return ret


@app.get("/collections/search", tags=['collections'], response_model=List[CollectionModel])
def search_collection(title: str,
                      current_user: int = Depends(get_current_user)):
    """
        Search for collections.

        *Currently only for admins*
    """
    with CollectionsService() as sce:
        with RightsThrower():
            matching_collections = sce.search(current_user, title)
    return matching_collections


@app.get("/collections/by_title", tags=['collections'], response_model=CollectionModel)
def collection_by_title(q: str):
    """
        Return the single collection with this title.
        For published datasets.
        !!! DO NOT MODIFY BEHAVIOR !!!
    """
    with CollectionsService() as sce:
        with RightsThrower():
            matching_collection = sce.query_by_title(q)
    return matching_collection


@app.get("/collections/by_short_title", tags=['collections'], response_model=CollectionModel)
def collection_by_short_title(q: str):
    """
        Return the single collection with this title.
        For published datasets.
        !!! DO NOT MODIFY BEHAVIOR !!!
    """
    with CollectionsService() as sce:
        with RightsThrower():
            matching_collection = sce.query_by_short_title(q)
    return matching_collection


@app.get("/collections/{collection_id}", tags=['collections'], response_model=CollectionModel)
def get_collection(collection_id: int,
                   current_user: int = Depends(get_current_user)):
    """
        Read a collection by its ID.

        *Currently only for admins*
    """
    with CollectionsService() as sce:
        with RightsThrower():
            present_collection = sce.query(current_user, collection_id, for_update=False)
        if present_collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return present_collection


@app.put("/collections/{collection_id}", tags=['collections'])
def update_collection(collection_id: int,
                      collection: CollectionModel,
                      current_user: int = Depends(get_current_user)):
    """
        Update the collection. Note that some updates are silently failing when not compatible
        with the composing projects.

        *Currently only for admins*
    """
    with CollectionsService() as sce:
        with RightsThrower():
            present_collection = sce.query(current_user, collection_id, for_update=True)
        if present_collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        # noinspection PyUnresolvedReferences
        present_collection.update(session=sce.session,
                                  title=collection.title,
                                  short_title=collection.short_title,
                                  project_ids=collection.project_ids,
                                  provider_user=collection.provider_user, contact_user=collection.contact_user,
                                  citation=collection.citation, abstract=collection.abstract,
                                  description=collection.description,
                                  creator_users=collection.creator_users, associate_users=collection.associate_users,
                                  creator_orgs=collection.creator_organisations,
                                  associate_orgs=collection.associate_organisations)


@app.get("/collections/{collection_id}/export/emodnet", tags=['collections'], response_model=EMODnetExportRsp)
def emodnet_format_export(collection_id: int,
                          dry_run: bool,
                          with_zeroes: bool,
                          auto_morpho: bool,
                          with_computations: bool,
                          current_user: int = Depends(get_current_user)) -> EMODnetExportRsp:
    """
        Export the collection in EMODnet format, @see https://www.emodnet-ingestion.eu/
        Produces a DwC-A archive into a temporary directory, ready for download.
        - param `dry_run`: If set, then only a diagnostic of doability will be done.
        - param `with_zeroes`: If set, then *absent* records will be generated, in the relevant samples,
         for categories present in other samples.
        - param `with_computations`: If set, then an attempt will be made to compute organisms concentrations
        and biovolumes.
        - param `auto_morpho`: If set, then any object classified on a Morpho category will be added to
         the count of the nearest Phylo parent, upward in the tree.

        Maybe useful, a reader in Python: https://python-dwca-reader.readthedocs.io/en/latest/index.html

        *Currently only for admins*
    """
    with EMODnetExport(collection_id, dry_run, with_zeroes, with_computations, auto_morpho) as sce:
        with RightsThrower():
            return sce.run(current_user)


@app.delete("/collections/{collection_id}", tags=['collections'])
def erase_collection(collection_id: int,
                     current_user: int = Depends(get_current_user)) -> int:
    """
        Delete the collection, i.e. the precious fields, as the projects are just linked-at from the collection.
    """
    with CollectionsService() as sce:
        with RightsThrower():
            return sce.delete(current_user, collection_id)


# ######################## END OF COLLECTION

MyORJSONResponse.register(ProjectBO, ProjectModel)
MyORJSONResponse.register(User, UserModel)

project_model_columns = plain_columns(ProjectModel)


# TODO TODO TODO: No verification of GET query parameters by FastAPI. pydantic does POST models OK.
@app.get("/projects/search", tags=['projects'], response_model=List[ProjectModel])
def search_projects(current_user: Optional[int] = Depends(get_optional_current_user),
                    also_others: bool = Query(default=False, deprecated=True),
                    not_granted: bool = False,
                    for_managing: bool = False,
                    title_filter: str = '',
                    instrument_filter: str = '',
                    filter_subset: bool = False,
                    order_field: Optional[str] = Query(default=None,
                                                       description="One of %s" % list(project_model_columns.keys())),
                    window_start: Optional[int] = Query(default=None,
                                                        description="Skip `window_start` before returning data"),
                    window_size: Optional[int] = Query(default=None,
                                                       description="Return only `window_size` lines")
                    ) -> MyORJSONResponse:  # List[ProjectBO]
    """
        Return projects which the current user has explicit permission to access, with search options.
        - `param` not_granted: Return projects on which the current user has _no permission_, but visible to him/her
        - `param` for_managing: Return projects that can be written to (including erased) by the current user
        - `param` title_filter: Use this pattern for matching returned projects names
        - `param` instrument_filter: Only return projects where this instrument was used
        - `param` filter_subset: Only return projects having 'subset' in their names
        - `params` order_field, window_start, window_size: See accompanying description.
    """
    not_granted = not_granted or also_others
    with ProjectsService() as sce:
        ret = sce.search(current_user_id=current_user, not_granted=not_granted, for_managing=for_managing,
                         title_filter=title_filter, instrument_filter=instrument_filter, filter_subset=filter_subset)
    # The DB query takes a few ms, and enrich not much more, so we can afford to narrow the search on the result
    ret = sort_and_prune(ret, order_field, project_model_columns, window_start, window_size)
    return MyORJSONResponse(ret)


@app.post("/projects/create", tags=['projects'])
def create_project(params: CreateProjectReq,
                   current_user: int = Depends(get_current_user)) -> Union[int, str]:
    """
        Create an empty project with only a title, and return its number.
        The project will be managed by current user.
        The user has to be app administrator or project creator.
    """
    with ProjectsService() as sce:
        with RightsThrower():
            ret = sce.create(current_user, params)
    if isinstance(ret, str):
        raise HTTPException(status_code=404, detail=ret)
    with DBSyncService(Project, Project.projid, ret) as ssce: ssce.wait()
    return ret


@app.post("/projects/{project_id}/subset", tags=['projects'], response_model=SubsetRsp)
def project_subset(project_id: int,
                   params: SubsetReq,
                   current_user: int = Depends(get_current_user)):
    """
        Subset a project into another one.
    """
    with SubsetServiceOnProject(project_id, params) as sce:
        with RightsThrower():
            ret = sce.run(current_user)
    return ret


@app.get("/projects/{project_id}", tags=['projects'], response_model=ProjectModel)
def project_query(project_id: int,
                  for_managing: Optional[bool] = False,
                  current_user: Optional[int] = Depends(get_optional_current_user)) -> ProjectBO:
    """
        Read project if it exists for current user, eventually for managing it.
    """
    with ProjectsService() as sce:
        for_managing = bool(for_managing)
        with RightsThrower():
            ret = sce.query(current_user, project_id, for_managing, for_update=False)
        return ret


@app.get("/project_set/taxo_stats", tags=['projects'], response_model=List[ProjectTaxoStatsModel])  # type: ignore
def project_set_get_stats(ids: str,
                          taxa_ids: Optional[str] = "",
                          current_user: Optional[int] = Depends(get_optional_current_user)) -> List[ProjectTaxoStats]:
    """
        Read projects statistics, i.e. used taxa and classification states.

        If several `ìds` are provided, one stat record will be returned per project.
        If several `taxa_ids` are provided, one stat record will be returned per requested taxa, if populated.
        If `taxa_ids` is 'all', all valued taxa in the project(s) are returned.
    """
    with ProjectsService() as sce:
        num_prj_ids = _split_num_list(ids)
        if taxa_ids == 'all':
            num_taxa_ids = taxa_ids
        else:
            num_taxa_ids = _split_num_list(taxa_ids)
        with RightsThrower():
            ret = sce.read_stats(current_user, num_prj_ids, num_taxa_ids)
        return ret


@app.get("/project_set/user_stats", tags=['projects'], response_model=List[ProjectUserStatsModel])  # type: ignore
def project_set_get_user_stats(ids: str,
                               current_user: int = Depends(get_current_user)) -> List[ProjectUserStats]:
    """
        Read projects user statistics, i.e. a summary of the work done by users in the
        required projects. The returned values are a detail _per project_, so size of input list
        equals size of output list.
    """
    with ProjectsService() as sce:
        num_ids = _split_num_list(ids)
        with RightsThrower():
            ret = sce.read_user_stats(current_user, num_ids)
        return ret


@app.post("/projects/{project_id}/dump", tags=['projects'], include_in_schema=False)  # pragma:nocover
def project_dump(project_id: int,
                 filters: ProjectFiltersModel,
                 current_user: int = Depends(get_current_user)):
    """
        Dump the project in JSON form. Internal so far.
    """
    # TODO: Use a StreamingResponse to avoid buffering
    with JsonDumper(current_user, project_id, filters) as sce:
        # TODO: Finish. lol.
        import sys
        return sce.run(sys.stdout)


@app.post("/projects/{project_id}/merge", tags=['projects'], response_model=MergeRsp)
def project_merge(project_id: int,
                  source_project_id: int,
                  dry_run: bool,
                  current_user: int = Depends(get_current_user)) -> MergeRsp:
    """
        Merge another project into this one. It's more a phagocytosis than a merge, as the source will see
        all its objects gone and will be erased.
        - param `dry_run`: If set, then only a diagnostic of doability will be done.
    """
    with MergeService(project_id, source_project_id, dry_run) as sce:
        with RightsThrower():
            return sce.run(current_user)


@app.get("/projects/{project_id}/check", tags=['projects'])
def project_check(project_id: int,
                  current_user: int = Depends(get_current_user)):
    """
        Check consistency of a project.
    """
    with ProjectConsistencyChecker(project_id) as sce:
        with RightsThrower():
            return sce.run(current_user)


@app.get("/projects/{project_id}/stats", tags=['projects'])
def project_stats(project_id: int,
                  current_user: int = Depends(get_current_user)):
    """
        Check consistency of a project.
    """
    with ProjectStatsFetcher(project_id) as sce:
        with RightsThrower():
            return sce.run(current_user)


@app.post("/projects/{project_id}/recompute_geo", tags=['projects'])
def project_recompute_geography(project_id: int,
                                current_user: int = Depends(get_current_user)) -> None:
    """
        Recompute geography information for all samples in project.
    """
    with ProjectsService() as sce:
        with RightsThrower():
            sce.recompute_geo(current_user, project_id)


@app.post("/file_import/{project_id}", tags=['projects'], response_model=ImportRsp)
def import_file(project_id: int,
                params: ImportReq,
                current_user: int = Depends(get_current_user)):
    """
        Validate or do a real import of an EcoTaxa archive or directory.
    """
    with FileImport(project_id, params) as sce:
        with RightsThrower():
            ret = sce.run(current_user)
    return ret


@app.post("/simple_import/{project_id}", tags=['projects'], response_model=SimpleImportRsp)
def simple_import(project_id: int,
                  params: SimpleImportReq,
                  dry_run: bool,
                  current_user: int = Depends(get_current_user)):
    """
        Import images only, with same metadata for all.
        - param `dry_run`: If set, then _only_ a diagnostic of do-ability will be done.
            In this case, plain value check.
        If no dry_run, this call will create a background job.
    """
    with SimpleImport(project_id, params, dry_run) as sce:
        with RightsThrower():
            ret = sce.run(current_user)
    return ret


@app.delete("/projects/{project_id}", tags=['projects'])
def erase_project(project_id: int,
                  only_objects: bool = False,
                  current_user: int = Depends(get_current_user)) -> Tuple[int, int, int, int]:
    """
        Delete the project.
            Optionally, if "only_objects" is set, the project structure is kept,
                but emptied from any object/sample/acquisition/process
            Otherwise, no trace of the project will remain in the database.
    """
    with ProjectsService() as sce:
        with RightsThrower():
            return sce.delete(current_user, project_id, only_objects)


@app.put("/projects/{project_id}", tags=['projects'])
def update_project(project_id: int,
                   project: ProjectModel,
                   current_user: int = Depends(get_current_user)):
    """
        Update the project.
        Note that some fields will NOT be updated and simply ignored, e.g. *free_cols.
    """
    with ProjectsService() as sce:
        with RightsThrower():
            present_project: ProjectBO = sce.query(current_user, project_id, for_managing=True, for_update=True)

        with ValidityThrower():
            # noinspection PyUnresolvedReferences
            present_project.update(session=sce.session,
                                   title=project.title, visible=project.visible, status=project.status,
                                   projtype=project.projtype,
                                   init_classif_list=project.init_classif_list,
                                   classiffieldlist=project.classiffieldlist, popoverfieldlist=project.popoverfieldlist,
                                   cnn_network_id=project.cnn_network_id, comments=project.comments,
                                   contact=project.contact,
                                   managers=project.managers, annotators=project.annotators, viewers=project.viewers,
                                   license_=project.license)

    with DBSyncService(Project, Project.projid, project_id) as ssce: ssce.wait()
    with DBSyncService(ProjectPrivilege, ProjectPrivilege.projid, project_id) as ssce: ssce.wait()


# ######################## END OF PROJECT

@app.get("/samples/search", tags=['samples'], response_model=List[SampleModel])
def samples_search(project_ids: str,
                   id_pattern: str,
                   current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> List[SampleBO]:
    """
        Read samples for a set of projects.

        - project_ids: any(non number)-separated list of project numbers
        - id_pattern: sample id textual pattern. Use * or '' for 'any matches'. Match is case-insensitive.
    """
    with SamplesService() as sce:
        proj_ids = _split_num_list(project_ids)
        with RightsThrower():
            ret = sce.search(current_user, proj_ids, id_pattern)
        return ret


@app.get("/sample_set/taxo_stats", tags=['samples'], response_model=List[SampleTaxoStatsModel])  # type:ignore
def sample_set_get_stats(sample_ids: str,
                         current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> List[SampleTaxoStats]:
    """
        Read classification statistics for a set of samples.
        EXPECT A SLOW RESPONSE. No cache of such information anywhere.

        - sample_ids: any(non number)-separated list of sample numbers
    """
    with SamplesService() as sce:
        sample_ids = _split_num_list(sample_ids)
        with RightsThrower():
            ret = sce.read_taxo_stats(current_user, sample_ids)
        return ret


@app.post("/sample_set/update", tags=['samples'])
def update_samples(req: BulkUpdateReq,
                   current_user: int = Depends(get_current_user)) -> int:
    """
        Do the required update for each sample in the set. Any non-null field in the model is written to
        every impacted sample.
            Return the number of updated entities.
    """
    with SamplesService() as sce:
        with RightsThrower():
            return sce.update_set(current_user, req.target_ids, req.updates)


@app.get("/sample/{sample_id}", tags=['samples'], response_model=SampleModel)
def sample_query(sample_id: int,
                 current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> SampleBO:
    """
        Read a single object.
    """
    with SamplesService() as sce:
        with RightsThrower():
            ret = sce.query(current_user, sample_id)
        if ret is None:
            raise HTTPException(status_code=404, detail="Sample not found")
        return ret


# ######################## END OF SAMPLE

@app.get("/acquisitions/search", tags=['acquisitions'], response_model=List[AcquisitionModel])
def acquisitions_search(project_id: int,
                        current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> List[AcquisitionBO]:
    """
        Read all acquisitions for a project.
    """
    with AcquisitionsService() as sce:
        with RightsThrower():
            ret = sce.search(current_user, project_id)
        return ret


@app.post("/acquisition_set/update", tags=['acquisitions'])
def update_acquisitions(req: BulkUpdateReq,
                        current_user: int = Depends(get_current_user)) -> int:
    """
        Do the required update for each acquisition in the set.
            Return the number of updated entities.
    """
    with AcquisitionsService() as sce:
        with RightsThrower():
            return sce.update_set(current_user, req.target_ids, req.updates)


@app.get("/acquisition/{acquisition_id}", tags=['acquisitions'], response_model=AcquisitionModel)
def acquisition_query(acquisition_id: int,
                      current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> AcquisitionBO:
    """
        Read a single object.
    """
    with AcquisitionsService() as sce:
        with RightsThrower():
            ret = sce.query(current_user, acquisition_id)
        if ret is None:
            raise HTTPException(status_code=404, detail="Acquisition not found")
        return ret


# ######################## END OF ACQUISITION

@app.get("/instruments/", tags=['instrument'], response_model=List[str])
def instrument_query(project_ids: str) \
        -> List[str]:
    """
        Query for instruments, inside specific project(s).
    """
    with InstrumentsService() as sce:
        proj_ids = _split_num_list(project_ids)
        with RightsThrower():
            ret = sce.query(proj_ids)
        return ret


# ######################## END OF INSTRUMENT

@app.post("/process_set/update", tags=['processes'], response_model=int)
def update_processes(req: BulkUpdateReq,
                     current_user: int = Depends(get_current_user)) -> int:
    """
        Do the required update for each process in the set.
            Return the number of updated entities.
    """
    with ProcessesService() as sce:
        with RightsThrower():
            return sce.update_set(current_user, req.target_ids, req.updates)


@app.get("/process/{process_id}", tags=['processes'], response_model=ProcessModel)
def process_query(process_id: int,
                  current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> ProcessBO:
    """
        Read a single object.
    """
    with ProcessesService() as sce:
        with RightsThrower():
            ret = sce.query(current_user, process_id)
        if ret is None:
            raise HTTPException(status_code=404, detail="Process not found")
        return ret


# ######################## END OF PROCESS

# TODO: Should be app.get, but for this we need a way to express
#  that each field in ProjectFilter is part of the params

# TODO /query pas bon!

@app.post("/object_set/{project_id}/query", tags=['objects'], response_model=ObjectSetQueryRsp,
          response_class=MyORJSONResponse  # Force the ORJSON encoder
          )
def get_object_set(project_id: int,
                   filters: ProjectFiltersModel,
                   fields: Optional[str] = None,
                   order_field: Optional[str] = None,
                   # TODO: order_field should be a user-visible field name, not nXXX, in case of free field
                   window_start: Optional[int] = None,
                   window_size: Optional[int] = None,
                   current_user: Optional[int] = Depends(get_optional_current_user)) -> ObjectSetQueryRsp:
    """
        Return object ids for the given project with the filters.

        Optionally:

            - fields will specify the needed object (and ancilliary entities) fields
            - order_field will order the result using given field, If prefixed with "-" then it will be reversed.
            - window_start & window_size allows to return only a slice of the result.

        Fields follow the naming convention: `prefix.field`.
            Prefix is either 'obj' for main object, 'fre' for free fields, 'img' for the visible image.
            - Column obj.imgcount contains the total count of images for the object.
    """
    return_fields = None
    if fields is not None:
        return_fields = fields.split(",")
    with ObjectManager() as sce:
        with RightsThrower():
            rsp = ObjectSetQueryRsp()
            obj_with_parents, details, total = sce.query(current_user, project_id, filters,
                                                         return_fields, order_field,
                                                         window_start, window_size)
        rsp.total_ids = total
        rsp.object_ids = [with_p[0] for with_p in obj_with_parents]
        rsp.acquisition_ids = [with_p[1] for with_p in obj_with_parents]
        rsp.sample_ids = [with_p[2] for with_p in obj_with_parents]
        rsp.project_ids = [with_p[3] for with_p in obj_with_parents]
        rsp.details = details
        # TODO: Despite the ORJSON encode above, this response is still quite slow due to many calls
        # to def jsonable_encoder (in FastAPI encoders.py)
        return rsp


@app.post("/object_set/{project_id}/summary", tags=['objects'], response_model=ObjectSetSummaryRsp)
def get_object_set_summary(project_id: int,
                           only_total: bool,
                           filters: ProjectFiltersModel,
                           current_user: Optional[int] = Depends(get_optional_current_user)) -> ObjectSetSummaryRsp:
    """
        For the given project, with given filters, return the classification summary, i.e.:
            - Total number of objects
        Also if 'only_total' is not set:
            - Number of Validated ones
            - Number of Dubious ones
            - Number of Predicted ones
    """
    with ObjectManager() as sce:
        with RightsThrower():
            rsp = ObjectSetSummaryRsp()
            rsp.total_objects, rsp.validated_objects, rsp.dubious_objects, rsp.predicted_objects \
                = sce.summary(current_user, project_id, filters, only_total)
        return rsp


@app.post("/object_set/{project_id}/reset_to_predicted", tags=['objects'], response_model=None)
def reset_object_set_to_predicted(project_id: int,
                                  filters: ProjectFiltersModel,
                                  current_user: int = Depends(get_current_user)) -> None:
    """
        Reset to Predicted all objects for the given project with the filters.
    """
    with ObjectManager() as sce:
        with RightsThrower():
            return sce.reset_to_predicted(current_user, project_id, filters)


@app.post("/object_set/{project_id}/revert_to_history", tags=['objects'],
          response_model=ObjectSetRevertToHistoryRsp)
def revert_object_set_to_history(project_id: int,
                                 filters: ProjectFiltersModel,
                                 dry_run: bool,
                                 target: Optional[int] = None,
                                 current_user: int = Depends(get_current_user)) -> ObjectSetRevertToHistoryRsp:
    """
        Revert all objects for the given project, with the filters, to the target.
        - param `filters`: The set of filters to apply to get the target objects.
        - param `dry_run`: If set, then no real write but consequences of the revert will be replied.
        - param `target`: Use null/None for reverting using the last annotation from anyone, or a user id
            for the last annotation from this user.
    """
    with ObjectManager() as sce:
        with RightsThrower():
            obj_hist, classif_info = sce.revert_to_history(current_user, project_id, filters, dry_run, target)
        return ObjectSetRevertToHistoryRsp(last_entries=obj_hist,
                                           classif_info=classif_info)


@app.post("/object_set/update", tags=['objects'])
def update_object_set(req: BulkUpdateReq,
                      current_user: int = Depends(get_current_user)) -> int:
    """
        Update all the objects with given IDs and values
        Current user needs Manage right on all projects of specified objects.
    """
    with ObjectManager() as sce:
        with RightsThrower():
            return sce.update_set(current_user, req.target_ids, req.updates)


@app.post("/object_set/classify", tags=['objects'])
def classify_object_set(req: ClassifyReq,
                        current_user: int = Depends(get_current_user)) -> int:
    """
        Change classification and/or qualification for a set of objects.
        Current user needs at least Annotate right on all projects of specified objects.
    """
    assert len(req.target_ids) == len(req.classifications), "Need the same number of objects and classifications"
    with ObjectManager() as sce:
        with RightsThrower():
            ret, prj_id, changes = sce.classify_set(current_user, req.target_ids, req.classifications,
                                                    req.wanted_qualification)
        last_classif_ids = [change[2] for change in changes.keys()]  # Recently used are in first
        with UserService() as usce: usce.update_classif_mru(current_user, prj_id, last_classif_ids)
        with DBSyncService(ProjectTaxoStat, ProjectTaxoStat.projid, prj_id) as ssce: ssce.wait()
        return ret


@app.post("/object_set/classify_auto", tags=['objects'])
def classify_auto_object_set(req: ClassifyAutoReq,
                             current_user: int = Depends(get_current_user)) -> int:
    """
        Set automatic classification of a set of objects.
         - `params`: None, all is in the Request body.
    """
    assert len(req.target_ids) == len(req.classifications) == len(req.scores), \
        "Need the same number of objects, classifications and scores"
    with ObjectManager() as sce:
        with RightsThrower():
            ret, prj_id, changes = sce.classify_auto_set(current_user, req.target_ids, req.classifications, req.scores,
                                                         req.keep_log)
        with DBSyncService(ProjectTaxoStat, ProjectTaxoStat.projid, prj_id) as ssce: ssce.wait()
        return ret


# TODO: For small lists we could have a GET
@app.post("/object_set/parents", tags=['objects'], response_model=ObjectSetQueryRsp,
          response_class=MyORJSONResponse  # Force the ORJSON encoder
          )
def query_object_set_parents(object_ids: ObjectIDListT,
                             current_user: int = Depends(get_current_user)) -> ObjectSetQueryRsp:
    """
        Return object ids, with parent ones and projects for the objects in given list.
    """
    with ObjectManager() as sce:
        with RightsThrower():
            rsp = ObjectSetQueryRsp()
            obj_with_parents = sce.parents_by_id(current_user, object_ids)
        rsp.object_ids = [with_p[0] for with_p in obj_with_parents]
        rsp.acquisition_ids = [with_p[1] for with_p in obj_with_parents]
        rsp.sample_ids = [with_p[2] for with_p in obj_with_parents]
        rsp.project_ids = [with_p[3] for with_p in obj_with_parents]
        rsp.total_ids = len(rsp.object_ids)
        return rsp


@app.post("/object_set/export", tags=['objects'], response_model=ExportRsp)
def export_object_set(filters: ProjectFiltersModel,
                      request: ExportReq,
                      current_user: Optional[int] = Depends(get_optional_current_user)) -> ExportRsp:
    """
        Start an export job for the given object set and options.
    """
    with ProjectExport(request, filters) as sce:
        rsp = sce.run(current_user)
    return rsp


@app.delete("/object_set/", tags=['objects'])
def erase_object_set(object_ids: ObjectIDListT,
                     current_user: int = Depends(get_current_user)) -> Tuple[int, int, int, int]:
    """
        Delete the objects with given object ids.
        Current user needs Manage right on all projects of specified objects.
    """
    with ObjectManager() as sce:
        with RightsThrower():
            return sce.delete(current_user, object_ids)


@app.get("/object/{object_id}", tags=['object'], response_model=ObjectModel)
def object_query(object_id: int,
                 current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> ObjectBO:
    """
        Read a single object. Anonymous reader can do if the project has the right rights :)
    """
    with ObjectService() as sce:
        with RightsThrower():
            ret = sce.query(current_user, object_id)
        if ret is None:
            raise HTTPException(status_code=404, detail="Object not found")
        return ret


@app.get("/object/{object_id}/history", tags=['object'],
         response_model=List[HistoricalClassificationModel])  # type:ignore
def object_query_history(object_id: int,
                         current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> List[HistoricalClassification]:
    """
        Read a single object's history.
    """
    with ObjectService() as sce:
        with RightsThrower():
            ret = sce.query_history(current_user, object_id)
        if ret is None:
            raise HTTPException(status_code=404, detail="Object not found")
        return ret


# ######################## END OF OBJECT

@app.get("/taxa", tags=['Taxonomy Tree'], response_model=List[TaxonModel])
async def query_root_taxa() \
        -> List[TaxonBO]:
    """
        Return all taxa with no parent.
    """
    with TaxonomyService() as sce:
        ret = sce.query_roots()
        return ret


@app.get("/taxa/status", tags=['Taxonomy Tree'], response_model=TaxonomyTreeStatus)
async def taxa_tree_status(current_user: int = Depends(get_current_user)):
    """
        Return the status of taxonomy tree w/r to freshness.
    """
    with TaxonomyService() as sce:
        refresh_date = sce.status(_current_user_id=current_user)
        return TaxonomyTreeStatus(last_refresh=refresh_date.isoformat() if refresh_date else None)


@app.get("/taxon/{taxon_id}", tags=['Taxonomy Tree'], response_model=TaxonModel)
async def query_taxa(taxon_id: int,
                     _current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> Optional[TaxonBO]:
    """
        Information about a single taxon, including its lineage.
    """
    with TaxonomyService() as sce:
        ret = sce.query(taxon_id)
        return ret


@app.get("/taxon_set/search", tags=['Taxonomy Tree'], response_model=List[TaxaSearchRsp])
async def search_taxa(query: str,
                      project_id: Optional[int] = None,
                      current_user: Optional[int] = Depends(get_optional_current_user)):
    """
        Search for taxa by name.

        Queries can be 'small', i.e. of length < 3 and even zero-length.
        For a public, unauthenticated call:
        - zero-length and small queries always return nothing.
        - otherwise, a full search is done and results are returned in alphabetical order.

        Behavior for an authenticated call:
        - zero-length queries: return the MRU list in full.
        - small queries: the MRU list is searched, so that taxa in the recent list are returned, if matching.
        - otherwise, a full search is done. Results are ordered so that taxa in the project list are in first,
            and are signalled as such in the response.
    """
    with TaxonomyService() as sce:
        ret = sce.search(current_user_id=current_user, prj_id=project_id, query=query)
        return ret


@app.get("/taxon_set/query", tags=['Taxonomy Tree'], response_model=List[TaxonModel])
async def query_taxa_set(ids: str,
                         _current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> List[TaxonBO]:
    """
        Information about several taxa, including their lineage.
        The separator between numbers is arbitrary non-digit, e.g. ":", "|" or ","
    """
    with TaxonomyService() as sce:
        num_ids = _split_num_list(ids)
        ret = sce.query_set(num_ids)
        return ret


@app.get("/taxon/central/{taxon_id}", tags=['Taxonomy Tree'])
async def get_taxon_in_central(taxon_id: int,
                               _current_user: int = Depends(get_current_user)):
    """
        Get EcoTaxoServer full record for this taxon.
    """
    with CentralTaxonomyService() as sce:
        return sce.get_taxon_by_id(taxon_id)


# Below pragma is because we need the same params as EcoTaxoServer, but we just relay them
# noinspection PyUnusedLocal
@app.put("/taxon/central", tags=['Taxonomy Tree'])
async def add_taxon_in_central(name: str,
                               parent_id: int,  # We don't let users create a root taxon
                               taxotype: str,
                               creator_email: str,
                               request: Request,
                               source_desc: Optional[str] = None,
                               source_url: Optional[str] = None,
                               current_user: int = Depends(get_current_user)):
    """
        Create a taxon on EcoTaxoServer.
        Logged user must be manager (on any project) or application admin.
    """
    with CentralTaxonomyService() as sce:
        # Clone params which are immutable
        params = {k: v for k, v in request.query_params.items()}
        return sce.add_taxon(current_user, params)


@app.get("/taxa/stats/push_to_central", tags=['Taxonomy Tree'])
async def push_taxa_stats_in_central(_current_user: int = Depends(get_current_user)):
    """
        Push present instance stats into EcoTaxoServer.
    """
    with CentralTaxonomyService() as sce:
        return sce.push_stats()


@app.get("/worms/{aphia_id}", tags=['Taxonomy Tree'], include_in_schema=False, response_model=TaxonModel)
async def query_taxa_in_worms(aphia_id: int,
                              _current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> Optional[TaxonBO]:
    """
        Information about a single taxon in WoRMS reference, including its lineage.
    """
    with TaxonomyService() as sce:
        ret = sce.query_worms(aphia_id)
        return ret


@app.get("/taxa_ref_change/refresh", tags=['WIP'], include_in_schema=False,
         status_code=status.HTTP_200_OK)
async def refresh_taxa_db(max_requests: int,
                          current_user: int = Depends(get_current_user)) -> StreamingResponse:  # pragma:nocover
    """
        Refresh local mirror of WoRMS database.
    """
    with TaxonomyChangeService(max_requests) as sce:
        with RightsThrower():
            tsk = sce.db_refresh(current_user)
            async_bg_run(tsk)  # Run in bg while streaming logs
        # Below produces a chunked HTTP encoding, which is officially only HTTP 1.1 protocol
        return StreamingResponse(log_streamer(sce.temp_log, "Done,"), media_type="text/plain")


@app.get("/taxa_ref_change/check/{aphia_id}", tags=['WIP'], include_in_schema=False,
         status_code=status.HTTP_200_OK)
async def check_taxa_db(aphia_id: int,
                        current_user: int = Depends(get_current_user)) -> Response:  # pragma:nocover
    """
        Check that the given aphia_id is correctly stored.
    """
    with TaxonomyChangeService(1) as sce:
        with RightsThrower():
            msg = await sce.check_id(current_user, aphia_id)
        # Below produces a chunked HTTP encoding, which is officially only HTTP 1.1 protocol
        return Response(msg, media_type="text/plain")


@app.get("/taxa_ref_change/matches", tags=['WIP'], include_in_schema=False,
         status_code=status.HTTP_200_OK)
async def matching_with_worms_nice(request: Request,
                                   current_user: int = 0  # Depends(get_current_user)
                                   ) -> Response:  # pragma:nocover
    """
        Show current state of matches - HTML version.
    """
    params = request.query_params
    with TaxonomyChangeService(0) as sce:
        with RightsThrower():
            # noinspection PyProtectedMember
            data = sce.matching(current_user, params._dict)
        return templates.TemplateResponse("worms.html",
                                          {"request": request, "matches": data, "params": params},
                                          headers=CRSF_header)


# ######################## END OF TAXA_REF

@app.get("/admin/images/{project_id}/digest", tags=['WIP'], include_in_schema=False,
         response_model=str)
def digest_project_images(project_id: int,
                          max_digests: Optional[int],
                          current_user: int = Depends(get_current_user)) -> str:
    """
        Compute digests for images referenced from a project.
    """
    max_digests = 1000 if max_digests is None else max_digests
    with ImageManagerService() as sce:
        with RightsThrower():
            data = sce.do_digests(current_user, project_id, max_digests)
        return data


@app.get("/admin/images/digest", tags=['WIP'], include_in_schema=False,
         response_model=str)
def digest_images(max_digests: Optional[int],
                  project_id: Optional[int] = None,
                  current_user: int = Depends(get_current_user)) -> str:
    """
        Compute digests if they are not.
    """
    max_digests = 1000 if max_digests is None else max_digests
    with ImageManagerService() as sce:
        with RightsThrower():
            data = sce.do_digests(current_user, prj_id=project_id, max_digests=max_digests)
        return data


@app.get("/admin/images/cleanup1", tags=['WIP'], include_in_schema=False,
         response_model=str)
def cleanup_images_1(project_id: int,
                     max_deletes: Optional[int] = None,
                     current_user: int = Depends(get_current_user)) -> str:
    """
        Remove duplicated images inside same object. Probably due to import update bug.
    """
    max_deletes = 10000 if max_deletes is None else max_deletes
    with ImageManagerService() as sce:
        with RightsThrower():
            data = sce.do_cleanup_dup_same_obj(current_user, prj_id=project_id, max_deletes=max_deletes)
        return data


@app.get("/admin/nightly", tags=['WIP'], include_in_schema=False,
         response_model=str)
def nightly_maintenance(current_user: int = Depends(get_current_user)) -> int:
    """
        Do nightly cleanups and calculations.
    """
    with NightlyJobService() as sce:
        with RightsThrower():
            data = sce.run(current_user)
        return data


# ######################## END OF ADMIN

@app.get("/jobs/", tags=['jobs'], response_model=List[JobModel])
def list_jobs(for_admin: bool,
              current_user: int = Depends(get_current_user)) -> List[JobBO]:
    """
        Return the jobs for current user, or all of them if admin and asked for.
    """
    with JobCRUDService() as sce:
        with RightsThrower():
            ret = sce.list(current_user, for_admin)
    return ret


@app.get("/jobs/{job_id}/", tags=['jobs'], response_model=JobModel)
def get_job(job_id: int,
            current_user: int = Depends(get_current_user)) -> JobBO:
    """
        Return the job by its id.
    """
    with JobCRUDService() as sce:
        with RightsThrower():
            ret = sce.query(current_user, job_id)
        return ret


@app.post("/jobs/{job_id}/answer", tags=['jobs'])
def reply_job_question(job_id: int,
                       reply: Dict[str, Any],
                       current_user: int = Depends(get_current_user)) -> None:
    """
        Send answers to last question. The job resumes after it receives the reply.
        Note: It's only about data storage here.
        If the data is technically NOK e.g. not a JS object, standard 422 error should be thrown.
        If the data is incorrect from consistency point of view, the job will return in Asking state.
    """
    with JobCRUDService() as sce:
        with RightsThrower():
            sce.reply(current_user, job_id, reply)


@app.get("/jobs/{job_id}/restart", tags=['jobs'])
def restart_job(job_id: int,
                current_user: int = Depends(get_current_user)):
    """
        Restart the job by its id.
        The job must be in a restartable state, and be accessible to current user.
    """
    with JobCRUDService() as sce:
        with RightsThrower():
            sce.restart(current_user, job_id)


@app.get("/jobs/{job_id}/log", tags=['jobs'])
def get_job_log_file(job_id: int,
                     current_user: int = Depends(get_current_user)) -> FileResponse:
    """
        Return the log file produced by given task.
        The task must belong to requester.
    """
    with JobCRUDService() as sce:
        with RightsThrower():
            path = sce.get_log_path(current_user, job_id)
        return FileResponse(str(path))


@app.get("/jobs/{job_id}/file", tags=['jobs'], responses={
    200: {
        "content": {"application/zip": {},
                    "text/tab-separated-values": {}},
        "description": "Return the produced file.",
    }
})
def get_job_file(job_id: int,
                 current_user: int = Depends(get_current_user)) -> StreamingResponse:
    """
        Return the file produced by given task.
        The task must belong to requester.
    """
    with JobCRUDService() as sce:
        with RightsThrower():
            file_like, file_name, media_type = sce.get_file_stream(current_user, job_id)
        headers = {"content-disposition": "attachment; filename=\"" + file_name + "\""}
        return StreamingResponse(file_like, headers=headers, media_type=media_type)


@app.delete("/jobs/{job_id}", tags=['jobs'])
def erase_job(job_id: int,
              current_user: int = Depends(get_current_user)) -> int:
    """
        Delete the job, from DB and with associated storage.
        If the job is running then kill it.
    """
    with JobCRUDService() as sce:
        with RightsThrower():
            return sce.delete(current_user, job_id)


# ######################## END OF JOBS

@app.get("/my_files/{sub_path:path}", tags=['Files'], response_model=DirectoryModel)
async def list_user_files(sub_path: str,
                          current_user: int = Depends(get_current_user)) -> DirectoryModel:
    """
        List the private files which are usable for some file-related operations e.g. import.
    """
    with UserFolderService() as sce:
        with RightsThrower():
            file_list = await sce.list(sub_path, current_user)
    return file_list


@app.post("/my_files/", tags=['Files'], response_model=str)
async def put_user_file(file: UploadFile = File(...),
                        path: Optional[str] = Form(None),
                        tag: Optional[str] = Form(None),
                        current_user: int = Depends(get_current_user)):
    """
        Upload a file for the current user. The returned text will contain a serve-side path
        which is usable for some file-related operations e.g. import.
    """
    with UserFolderService() as sce:
        with RightsThrower():
            file_name = await sce.store(current_user, file, path, tag)
        return file_name


@app.get("/common_files/", tags=['Files'], response_model=DirectoryModel)
async def list_common_files(path: str,
                            current_user: int = Depends(get_current_user)) -> DirectoryModel:
    """
        List the common files which are usable for some file-related operations e.g. import.
    """
    with CommonFolderService() as sce:
        with RightsThrower():
            file_list = await sce.list(path, current_user)
    return file_list


# ######################## END OF FILES

@app.get("/status", tags=['WIP'])
def system_status(_current_user: int = Depends(get_current_user)) -> Response:
    """
        Report the status, mainly used for verifying that the server is up.
    """
    with StatusService() as sce:
        return Response(sce.run(), media_type="text/plain")


@app.get("/error", tags=['misc'])
def system_error(_current_user: int = Depends(get_current_user)):
    """
        This entry point will return a 500 internal error, on purpose so the stack trace is visible and client
        can see what it gives.
    """
    with RightsThrower():
        assert False


@app.get("/noop", tags=['misc'], response_model=Union[ObjectHeaderModel,  # type: ignore
                                                      HistoricalClassificationModel])
def do_nothing(_current_user: int = Depends(get_current_user)):
    """
        This entry point will just do nothing.
            It's also used for exporting models we need on client side.
    """


@app.get("/constants", tags=['misc'], response_model=Constants)
def used_constants() -> Constants:
    """
        This entry point will return useful strings for user dialog.
        Now also used for values extracted from Config.
    """
    with ConstantsService() as sce:
        return sce.get()


# @app.get("/loadtest", tags=['WIP'], include_in_schema=False)
# def load_test() -> Response:
#     """
#         Simulate load with various response time. The Service() gets a session from the DB pool.
#         See if we just wait or fail to serve:
#         httperf --server=localhost --port=8000 --uri=/loadtest --num-conns=1000 --num-calls=10
#     """
#     with StatusService() as sce:
#     import time
#     time.sleep(random()/10)
#     return Response(sce.run(), media_type="text/plain")

app.add_exception_handler(status.HTTP_500_INTERNAL_SERVER_ERROR, internal_server_error_handler)

dump_openapi(app, __file__)


@app.on_event("startup")
def startup_event():
    JobScheduler.launch_at_interval(1)


@app.on_event("shutdown")
def shutdown_event():
    JobScheduler.shutdown()


def _split_num_list(ids):
    # Find first non-num char, decide it's a separator
    for c in ids:
        if c not in "0123456789":
            sep = c
            break
    else:
        sep = ","
    num_ids = [int(x) for x in ids.split(sep) if x.isdigit()]
    return num_ids
