# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Based on https://fastapi.tiangolo.com/
#
import os
from typing import Union, Tuple

from fastapi import FastAPI, Request, Response, status, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi_utils.timing import add_timing_middleware

from API_models.constants import Constants
from API_models.crud import *
from API_models.exports import EMODnetExportRsp
from API_models.imports import *
from API_models.login import LoginReq
from API_models.merge import MergeRsp
from API_models.objects import ObjectSetQueryRsp, ObjectSetRevertToHistoryRsp, ClassifyReq, ObjectModel, \
    ObjectHeaderModel, HistoricalClassificationModel, ObjectSetSummaryRsp
from API_models.subset import SubsetReq, SubsetRsp
from API_models.taxonomy import TaxaSearchRsp, TaxonModel, TaxonomyTreeStatus
from API_operations.CRUD.Collections import CollectionsService
from API_operations.CRUD.Object import ObjectService
from API_operations.CRUD.ObjectParents import SamplesService, AcquisitionsService, ProcessesService
from API_operations.CRUD.Projects import ProjectsService
from API_operations.CRUD.Tasks import TaskService
from API_operations.CRUD.Users import UserService
from API_operations.Consistency import ProjectConsistencyChecker
from API_operations.JsonDumper import JsonDumper
from API_operations.Merge import MergeService
from API_operations.ObjectManager import ObjectManager
from API_operations.Stats import ProjectStatsFetcher
from API_operations.Status import StatusService
from API_operations.Subset import SubsetServiceOnProject
from API_operations.TaxoManager import TaxonomyChangeService
from API_operations.TaxonomyService import TaxonomyService
from API_operations.exports.EMODnet import EMODnetExport
from API_operations.imports.Import import ImportAnalysis, RealImport
from API_operations.imports.SimpleImport import SimpleImport
from BO.Acquisition import AcquisitionBO
from BO.Classification import HistoricalClassification
from BO.Object import ObjectBO
from BO.ObjectSet import ObjectIDListT
from BO.Preferences import Preferences
from BO.Process import ProcessBO
from BO.Project import ProjectBO, ProjectStats
from BO.Rights import RightsBO
from BO.Sample import SampleBO
from BO.Taxonomy import TaxonBO
from helpers.Asyncio import async_bg_run, log_streamer
from helpers.DynamicLogs import get_logger
from helpers.fastApiUtils import internal_server_error_handler, dump_openapi, get_current_user, RightsThrower, \
    get_optional_current_user, MyORJSONResponse
from helpers.login import LoginService

logger = get_logger(__name__)

# TODO: A nicer API doc, see https://github.com/tiangolo/fastapi/issues/1140

app = FastAPI(title="EcoTaxa",
              version="0.0.6",
              # openapi URL as seen from navigator
              openapi_url="/api/openapi.json",
              # root_path="/API_models"
              default_response_class=MyORJSONResponse
              )

# Instrument a bit
add_timing_middleware(app, record=logger.info, prefix="app", exclude="untimed")

# HTML stuff
# app.mount("/styles", StaticFiles(directory="pages/styles"), name="styles")
templates = Jinja2Templates(directory=os.path.dirname(__file__) + "/pages/templates")
# Below is useless if proxied by legacy app
CDNs = " ".join(["cdn.datatables.net"])
CRSF_header = {
    'Content-Security-Policy': "default-src 'self' 'unsafe-inline' 'unsafe-eval' "
                               f"blob: data: {CDNs};frame-ancestors 'self';form-action 'self';"
}


# noinspection PyUnusedLocal
@app.post("/login", tags=['authentification'])
async def login(params: LoginReq) -> str:
    """
        Login barrier. If successful, the login will return a JWT which will have to be used
        in Bearer authentication scheme for subsequent calls.

        -`username`: User *email* which was used during registration

        -`password`: User password
    """
    with RightsThrower():
        return LoginService().validate_login(params.username, params.password)


# TODO: when python 3.7+, we can have pydantic generics and remove the ignore below
@app.get("/users", tags=['users'], response_model=List[UserModel])  # type:ignore
def get_users(current_user: int = Depends(get_current_user)):
    """
        Return the list of users. For admins only.
    """
    sce = UserService()
    return sce.list(current_user)


# TODO: when python 3.7+, we can have pydantic generics and remove the ignore below
@app.get("/users/me", tags=['users'], response_model=UserModelWithRights)  # type:ignore
def show_current_user(current_user: int = Depends(get_current_user)):
    """
        Return currently authenticated user. On top of DB fields, 'can_do' lists the allowed system-wide actions.
    """
    sce = UserService()
    ret = sce.search_by_id(current_user, current_user)
    assert ret is not None
    # noinspection PyTypeHints
    ret.can_do = RightsBO.allowed_actions(ret)  # type:ignore
    ret.last_used_projects = Preferences(ret).recent_projects(session=sce.session) # type:ignore
    return ret


@app.get("/users/my_preferences/{project_id}", tags=['users'], response_model=str)
def get_current_user_prefs(project_id: int,
                           key: str,
                           current_user: int = Depends(get_current_user)) -> str:
    """
        Return one preference, for project and currently authenticated user.
    """
    sce = UserService()
    return sce.get_preferences_per_project(current_user, project_id, key)


@app.put("/users/my_preferences/{project_id}", tags=['users'])
def set_current_user_prefs(project_id: int,
                           key: str,
                           value: str,
                           current_user: int = Depends(get_current_user)):
    """
        Set one preference, for project and currently authenticated user.
        -`key`: The preference key
        -`value`: The value to set this preference to
    """
    sce = UserService()
    return sce.set_preferences_per_project(current_user, project_id, key, value)


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


# TODO: when python 3.7+, we can have pydantic generics and remove the ignore below
@app.get("/users/{user_id}", tags=['users'], response_model=UserModel)  # type:ignore
def get_user(user_id: int,
             current_user: int = Depends(get_current_user)):
    """
        Return a single user by its id.
    """
    sce = UserService()
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
    sce = CollectionsService()
    with RightsThrower():
        ret = sce.create(current_user, params)
    if isinstance(ret, str):
        raise HTTPException(status_code=404, detail=ret)
    return ret


@app.get("/collections/search", tags=['collections'], response_model=List[CollectionModel])
def search_collection(title: str,
                      current_user: int = Depends(get_current_user)):
    """
        Search for collections.

        *Currently only for admins*
    """
    sce = CollectionsService()
    with RightsThrower():
        matching_collections = sce.search(current_user, title)
    return matching_collections


@app.get("/collections/{collection_id}", tags=['collections'], response_model=CollectionModel)
def get_collection(collection_id: int,
                   current_user: int = Depends(get_current_user)):
    """
        Read a collection by its ID.

        *Currently only for admins*
    """
    sce = CollectionsService()
    with RightsThrower():
        present_collection = sce.query(current_user, collection_id)
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
    sce = CollectionsService()
    with RightsThrower():
        present_collection = sce.query(current_user, collection_id)
    if present_collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    # noinspection PyUnresolvedReferences
    present_collection.update(session=sce.session,
                              title=collection.title,
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
                          current_user: int = Depends(get_current_user)) -> EMODnetExportRsp:
    """
        Export the collection in EMODnet format, @see https://www.emodnet-ingestion.eu/
        Produces a DwC-A archive into a temporary directory, ready for download.
        - param `dry_run`: If set, then only a diagnostic of doability will be done.
        Maybe useful, a reader in Python: https://python-dwca-reader.readthedocs.io/en/latest/index.html

        *Currently only for admins*
    """
    sce = EMODnetExport(collection_id, dry_run)
    with RightsThrower():
        return sce.run(current_user)


@app.delete("/collections/{collection_id}", tags=['collections'])
def erase_collection(collection_id: int,
                     current_user: int = Depends(get_current_user)) -> int:
    """
        Delete the collection, i.e. the precious fields, as the projects are just unliked from the collection.
    """
    sce = CollectionsService()
    with RightsThrower():
        return sce.delete(current_user, collection_id)


# ######################## END OF COLLECTION

@app.get("/projects/search", tags=['projects'], response_model=List[ProjectModel])
def search_projects(current_user: int = Depends(get_current_user),
                    also_others: bool = False,
                    for_managing: bool = False,
                    title_filter: str = '',
                    instrument_filter: str = '',
                    filter_subset: bool = False) -> List[ProjectBO]: # PABOPABOPABO
    """
        Return projects for current user.
        - `param` also_others: Allows to return projects for which given user has no right
        - `param` for_managing: Allows to return project that can be written to (including erased) by the given user
        - `param` title_filter: Use this pattern for matching returned projects names
        - `param` instrument_filter: Only return projects where this instrument was used
        - `param` filter_subset: Only return projects having 'subset' in their names
    """
    sce = ProjectsService()
    ret = sce.search(current_user_id=current_user, also_others=also_others, for_managing=for_managing,
                     title_filter=title_filter, instrument_filter=instrument_filter, filter_subset=filter_subset)
    return ret


@app.post("/projects/create", tags=['projects'])
def create_project(params: CreateProjectReq,
                   current_user: int = Depends(get_current_user)) -> Union[int, str]:
    """
        Create an empty project with only a title, and return its number.
        The project will be managed by current user.
        The user has to be app administrator or project creator.
    """
    sce = ProjectsService()
    with RightsThrower():
        ret = sce.create(current_user, params)
    if isinstance(ret, str):
        raise HTTPException(status_code=404, detail=ret)
    return ret


@app.post("/projects/{project_id}/subset", tags=['projects'], response_model=SubsetRsp)
def project_subset(project_id: int,
                   params: SubsetReq,
                   current_user: int = Depends(get_current_user)):
    """
        Subset a project into another one.
    """
    sce = SubsetServiceOnProject(project_id, params)
    with RightsThrower():
        return sce.run(current_user)


@app.get("/projects/{project_id}", tags=['projects'], response_model=ProjectModel)
def project_query(project_id: int,
                  for_managing: Optional[bool] = False,
                  current_user: Optional[int] = Depends(get_optional_current_user)) -> ProjectBO:
    """
        Read project if it exists for current user, eventually for managing it.
    """
    sce = ProjectsService()
    for_managing = bool(for_managing)
    with RightsThrower():
        ret = sce.query(current_user, project_id, for_managing)
    return ret


@app.get("/project_set/stats", tags=['projects'], response_model=List[ProjectStatsModel])
def project_set_get_stats(ids: str,
                          current_user: int = Depends(get_current_user)) -> List[ProjectStats]:
    """
        Read projects statistics, i.e. used taxa and classification states.
    """
    sce = ProjectsService()
    num_ids = _split_num_list(ids)
    with RightsThrower():
        ret = sce.read_stats(current_user, num_ids)
    return ret


@app.post("/projects/{project_id}/dump", tags=['projects'], include_in_schema=False)  # pragma:nocover
def project_dump(project_id: int,
                 filters: ProjectFiltersModel,
                 current_user: int = Depends(get_current_user)):
    """
        Dump the project in JSON form. Internal so far.
    """
    # TODO: Use a StreamingResponse to avoid buffering
    sce = JsonDumper(current_user, project_id, filters)
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
    sce = MergeService(project_id, source_project_id, dry_run)
    with RightsThrower():
        return sce.run(current_user)


@app.get("/projects/{project_id}/check", tags=['projects'])
def project_check(project_id: int,
                  current_user: int = Depends(get_current_user)):
    """
        Check consistency of a project.
    """
    sce = ProjectConsistencyChecker(project_id)
    with RightsThrower():
        return sce.run(current_user)


@app.get("/projects/{project_id}/stats", tags=['projects'])
def project_stats(project_id: int,
                  current_user: int = Depends(get_current_user)):
    """
        Check consistency of a project.
    """
    sce = ProjectStatsFetcher(project_id)
    with RightsThrower():
        return sce.run(current_user)


@app.post("/projects/{project_id}/recompute_geo", tags=['projects'])
def project_recompute_geography(project_id: int,
                                current_user: int = Depends(get_current_user)) -> None:
    """
        Recompute geography information for all samples in project.
    """
    sce = ProjectsService()
    with RightsThrower():
        sce.recompute_geo(current_user, project_id)


@app.post("/import_prep/{project_id}", tags=['projects'], response_model=ImportPrepRsp)
def import_preparation(project_id: int,
                       params: ImportPrepReq,
                       current_user: int = Depends(get_current_user)):
    """
        Prepare/validate the import of an EcoTaxa archive or directory.
    """
    sce = ImportAnalysis(project_id, params)
    with RightsThrower():
        return sce.run(current_user)


@app.post("/import_real/{project_id}", tags=['projects'], response_model=ImportRealRsp)
def real_import(project_id: int,
                params: ImportRealReq,
                current_user: int = Depends(get_current_user)):
    """
        Import an EcoTaxa archive or directory.
    """
    sce = RealImport(project_id, params)
    with RightsThrower():
        return sce.run(current_user)


@app.post("/simple_import/{project_id}", tags=['projects'], response_model=SimpleImportRsp)
def simple_import(project_id: int,
                  params: SimpleImportReq,
                  current_user: int = Depends(get_current_user)):
    """
        Import images only, with same metadata for all.
    """
    sce = SimpleImport(project_id, params)
    with RightsThrower():
        return sce.run(current_user)


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
    sce = ProjectsService()
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
    sce = ProjectsService()
    with RightsThrower():
        present_project: ProjectBO = sce.query(current_user, project_id, for_managing=True)
    # noinspection PyUnresolvedReferences
    present_project.update(session=sce.session,
                           title=project.title, visible=project.visible, status=project.status,
                           projtype=project.projtype,
                           init_classif_list=project.init_classif_list,
                           classiffieldlist=project.classiffieldlist, popoverfieldlist=project.popoverfieldlist,
                           cnn_network_id=project.cnn_network_id, comments=project.comments,
                           # owner=project.owner,
                           managers=project.managers, annotators=project.annotators, viewers=project.viewers,
                           license=project.license)


# ######################## END OF PROJECT

@app.get("/samples/search", tags=['samples'], response_model=List[SampleModel])
def samples_search(project_id: int,
                   current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> List[SampleBO]:
    """
        Read all samples for a project.
    """
    sce = SamplesService()
    with RightsThrower():
        ret = sce.search(current_user, project_id)
    return ret


@app.post("/sample_set/update", tags=['samples'])
def update_samples(req: BulkUpdateReq,
                   current_user: int = Depends(get_current_user)) -> int:
    """
        Do the required update for each sample in the set. Any non-null field in the model is written to
        every impacted sample.
            Return the number of updated entities.
    """
    sce = SamplesService()
    with RightsThrower():
        return sce.update_set(current_user, req.target_ids, req.updates)


@app.get("/sample/{sample_id}", tags=['samples'], response_model=SampleModel)
def sample_query(sample_id: int,
                 current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> SampleBO:
    """
        Read a single object.
    """
    sce = SamplesService()
    with RightsThrower():
        ret = sce.query(current_user, sample_id)
    if ret is None:
        raise HTTPException(status_code=404, detail="Sample not found")
    return ret


# ######################## END OF SAMPLE

@app.post("/acquisition_set/update", tags=['acquisitions'])
def update_acquisitions(req: BulkUpdateReq,
                        current_user: int = Depends(get_current_user)) -> int:
    """
        Do the required update for each acquisition in the set.
            Return the number of updated entities.
    """
    sce = AcquisitionsService()
    with RightsThrower():
        return sce.update_set(current_user, req.target_ids, req.updates)


@app.get("/acquisitions/search", tags=['acquisitions'], response_model=List[AcquisitionModel])
def acquisitions_search(project_id: int,
                        current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> List[AcquisitionBO]:
    """
        Read all acquisitions for a project.
    """
    sce = AcquisitionsService()
    with RightsThrower():
        ret = sce.search(current_user, project_id)
    return ret


@app.get("/acquisition/{acquisition_id}", tags=['acquisitions'], response_model=AcquisitionModel)
def acquisition_query(acquisition_id: int,
                      current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> AcquisitionBO:
    """
        Read a single object.
    """
    sce = AcquisitionsService()
    with RightsThrower():
        ret = sce.query(current_user, acquisition_id)
    if ret is None:
        raise HTTPException(status_code=404, detail="Acquisition not found")
    return ret


# ######################## END OF ACQUISITION

@app.post("/process_set/update", tags=['processes'], response_model=int)
def update_processes(req: BulkUpdateReq,
                     current_user: int = Depends(get_current_user)) -> int:
    """
        Do the required update for each process in the set.
            Return the number of updated entities.
    """
    sce = ProcessesService()
    with RightsThrower():
        return sce.update_set(current_user, req.target_ids, req.updates)


@app.get("/process/{process_id}", tags=['processes'], response_model=ProcessModel)
def process_query(process_id: int,
                  current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> ProcessBO:
    """
        Read a single object.
    """
    sce = ProcessesService()
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
                   order_field: Optional[str] = None,
                   # TODO: order_field should be a user-visible field name, not nXXX, in case of free field
                   window_start: Optional[int] = None,
                   window_size: Optional[int] = None,
                   current_user: Optional[int] = Depends(get_optional_current_user)) -> ObjectSetQueryRsp:
    """
        Return object ids for the given project with the filters.
        Optionally:
            - order_field will order the result using given field, If prefixed with "-" then it will be reversed.
            - window_start & window_size allows to return only a slice of the result.
    """
    sce = ObjectManager()
    with RightsThrower():
        rsp = ObjectSetQueryRsp()
        obj_with_parents, total = sce.query(current_user, project_id, filters, order_field, window_start, window_size)
    rsp.total_ids = total
    rsp.object_ids = [with_p[0] for with_p in obj_with_parents]
    rsp.acquisition_ids = [with_p[1] for with_p in obj_with_parents]
    rsp.sample_ids = [with_p[2] for with_p in obj_with_parents]
    rsp.project_ids = [with_p[3] for with_p in obj_with_parents]
    # TODO: Despite the ORJSON encode above, this response is still quite slow due to a call
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
    sce = ObjectManager()
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
    sce = ObjectManager()
    with RightsThrower():
        return sce.reset_to_predicted(current_user, project_id, filters)


@app.post("/object_set/{project_id}/revert_to_history", tags=['objects'], response_model=ObjectSetRevertToHistoryRsp)
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
    sce = ObjectManager()
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
    sce = ObjectManager()
    with RightsThrower():
        return sce.update_set(current_user, req.target_ids, req.updates)


@app.post("/object_set/classify", tags=['objects'])
def classify_object_set(req: ClassifyReq,
                        current_user: int = Depends(get_current_user)) -> int:
    """
        Change classification and/or qualification for a set of objects.
        Current user needs at least Annotate right on all projects of specified objects.
    """
    sce = ObjectManager()
    assert len(req.target_ids) == len(req.classifications), "Need the same number of objects and classifications"
    with RightsThrower():
        ret, prj_id, changes = sce.classify_set(current_user, req.target_ids, req.classifications,
                                                req.wanted_qualification)
    last_classif_ids = [change[2] for change in changes.keys()]  # Recently used are in first
    UserService().update_classif_mru(current_user, prj_id, last_classif_ids)
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
    sce = ObjectManager()
    with RightsThrower():
        rsp = ObjectSetQueryRsp()
        obj_with_parents = sce.parents_by_id(current_user, object_ids)
    rsp.object_ids = [with_p[0] for with_p in obj_with_parents]
    rsp.acquisition_ids = [with_p[1] for with_p in obj_with_parents]
    rsp.sample_ids = [with_p[2] for with_p in obj_with_parents]
    rsp.project_ids = [with_p[3] for with_p in obj_with_parents]
    rsp.total_ids = len(rsp.object_ids)
    return rsp


@app.delete("/object_set/", tags=['objects'])
def erase_object_set(object_ids: ObjectIDListT,
                     current_user: int = Depends(get_current_user)) -> Tuple[int, int, int, int]:
    """
        Delete the objects with given object ids.
        Current user needs Manage right on all projects of specified objects.
    """
    sce = ObjectManager()
    with RightsThrower():
        return sce.delete(current_user, object_ids)


@app.get("/object/{object_id}", tags=['object'], response_model=ObjectModel)
def object_query(object_id: int,
                 current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> ObjectBO:
    """
        Read a single object.
    """
    sce = ObjectService()
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
    sce = ObjectService()
    with RightsThrower():
        ret = sce.query_history(current_user, object_id)
    if ret is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return ret


@app.get("/taxa/status", tags=['Taxonomy Tree'], response_model=TaxonomyTreeStatus)
async def taxa_tree_status(current_user: int = Depends(get_current_user)):
    """
        Return the status of taxonomy tree w/r to freshness.
    """
    sce = TaxonomyService()
    refresh_date = sce.status(_current_user_id=current_user)
    return TaxonomyTreeStatus(last_refresh=refresh_date.isoformat() if refresh_date else None)


@app.get("/taxon_set/search", tags=['Taxonomy Tree'], response_model=List[TaxaSearchRsp])
async def search_taxa(query: str,
                      project_id: Optional[int],
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
    sce = TaxonomyService()
    ret = sce.search(current_user_id=current_user, prj_id=project_id, query=query)
    return ret


@app.get("/taxon/{taxon_id}", tags=['Taxonomy Tree'], response_model=TaxonModel)
async def query_taxa(taxon_id: int,
                     _current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> Optional[TaxonBO]:
    """
        Information about a single taxon, including its lineage.
    """
    sce = TaxonomyService()
    ret = sce.query(taxon_id)
    return ret


@app.get("/worms/{aphia_id}", tags=['Taxonomy Tree'], include_in_schema=False, response_model=TaxonModel)
async def query_taxa_in_worms(aphia_id: int,
                              _current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> Optional[TaxonBO]:
    """
        Information about a single taxon in WoRMS reference, including its lineage.
    """
    sce = TaxonomyService()
    ret = sce.query_worms(aphia_id)
    return ret


@app.get("/taxon_set/query", tags=['Taxonomy Tree'], response_model=List[TaxonModel])
async def query_taxa_set(ids: str,
                         _current_user: Optional[int] = Depends(get_optional_current_user)) \
        -> List[TaxonBO]:
    """
        Information about several taxa, including their lineage.
        The separator between numbers is arbitrary non-digit, e.g. ":", "|" or ","
    """
    sce = TaxonomyService()
    num_ids = _split_num_list(ids)
    ret = sce.query_set(num_ids)
    return ret


@app.get("/taxa_ref_change/refresh", tags=['WIP'], include_in_schema=False,
         status_code=status.HTTP_200_OK)
async def refresh_taxa_db(max_requests: int,
                          current_user: int = Depends(get_current_user)) -> StreamingResponse:  # pragma:nocover
    """
        Refresh local mirror of WoRMS database.
    """
    sce = TaxonomyChangeService(max_requests)
    tmp_log = sce.log_to_temp()
    logger.info("logging to %s", tmp_log)
    with RightsThrower():
        tsk = sce.db_refresh(current_user)
        async_bg_run(tsk)  # Run in bg while streaming logs
    # Below produces a chunked HTTP encoding, which is officially only HTTP 1.1 protocol
    return StreamingResponse(log_streamer(tmp_log, "Done,"), media_type="text/plain")


@app.get("/taxa_ref_change/check/{aphia_id}", tags=['WIP'], include_in_schema=False,
         status_code=status.HTTP_200_OK)
async def check_taxa_db(aphia_id: int,
                        current_user: int = Depends(get_current_user)) -> Response:  # pragma:nocover
    """
        Check that the given aphia_id is correctly stored.
    """
    sce = TaxonomyChangeService(1)
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
    sce = TaxonomyChangeService(0)
    with RightsThrower():
        # noinspection PyProtectedMember
        data = sce.matching(current_user, params._dict)
    return templates.TemplateResponse("worms.html",
                                      {"request": request, "matches": data, "params": params},
                                      headers=CRSF_header)


@app.get("/status", tags=['WIP'])
def system_status(_current_user: int = Depends(get_current_user)) -> Response:
    """
        Report the status, mainly used for verifying that the server is up.
    """
    sce = StatusService()
    return Response(sce.run(), media_type="text/plain")


@app.get("/tasks/{task_id}/file", tags=['task'], responses={
    200: {
        "content": {"application/zip": {}},
        "description": "Return the file.",
    }
})
def get_task_file(task_id: int,
                  current_user: int = Depends(get_current_user)) -> StreamingResponse:
    """
        Return the file produced by given task.
        The task must belong to requester.
    """
    sce = TaskService()
    with RightsThrower():
        file_like, file_name = sce.get_file_stream(current_user, task_id)
    headers = {"content-disposition": "attachment; filename=\"" + file_name + "\""}
    return StreamingResponse(file_like, headers=headers, media_type="application/zip")


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
    """
    return Constants()


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
