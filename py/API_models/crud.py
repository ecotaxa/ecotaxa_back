# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in CRUD API_operations.
#
from typing import Optional, Dict, Type, Iterable, List, Any

from sqlalchemy.sql.functions import current_timestamp
from typing_extensions import TypedDict

from BO.DataLicense import LicenseEnum
from DB import User, Project, Sample, Acquisition, Process
from DB.Acquisition import ACQUISITION_FREE_COLUMNS
from DB.Collection import Collection
from DB.Process import PROCESS_FREE_COLUMNS
from DB.Sample import SAMPLE_FREE_COLUMNS
from helpers.pydantic import BaseModel, Field
from .helpers.DBtoModel import sqlalchemy_to_pydantic
from .helpers.TypedDictToModel import typed_dict_to_model

# Enriched model
FreeColT = Dict[str, str]

# Direct mirror of DB models
_UserModelFromDB = sqlalchemy_to_pydantic(User, exclude=[User.password.name,
                                                         User.preferences.name])
_ProjectModelFromDB: Type = sqlalchemy_to_pydantic(Project, exclude=[Project.mappingobj.name,
                                                                     Project.mappingacq.name,
                                                                     Project.mappingprocess.name,
                                                                     Project.mappingsample.name,
                                                                     Project.initclassiflist.name,
                                                                     ] + [
                                                                        # Not replaced yet but LOTS of data
                                                                        Project.fileloaded.name
                                                                    ])


class ProjectSummaryModel(BaseModel):
    projid: int = Field(title="Project unique identifier")
    title: str = Field(title="Project title")


# We exclude free columns from base model, they will be mapped in a dedicated sub-entity
_SampleModelFromDB = sqlalchemy_to_pydantic(Sample,
                                            exclude=["t%02d" % i for i in range(1, SAMPLE_FREE_COLUMNS)])
_AcquisitionModelFromDB = sqlalchemy_to_pydantic(Acquisition,
                                                 exclude=["t%02d" % i for i in range(1, ACQUISITION_FREE_COLUMNS)])
_ProcessModelFromDB = sqlalchemy_to_pydantic(Process,
                                             exclude=["t%02d" % i for i in range(1, PROCESS_FREE_COLUMNS)])
_CollectionModelFromDB = sqlalchemy_to_pydantic(Collection,
                                                exclude=[Collection.contact_user_id.name,
                                                         Collection.provider_user_id.name])


class UserModel(_UserModelFromDB):  # type:ignore
    pass


class UserModelWithRights(_UserModelFromDB):  # type:ignore
    can_do: List[int] = Field(title="Actions allowed to this user, 1=create project, 2=administrate the app",
                              default=[])
    last_used_projects: List[ProjectSummaryModel] = Field(title="The last used projects for this user",
                                                          default=[])


class _AddedToProject(BaseModel):
    obj_free_cols: FreeColT = Field(title="Object free columns",
                                    default={})
    sample_free_cols: FreeColT = Field(title="Sample free columns",
                                       default={})
    acquisition_free_cols: FreeColT = Field(title="Acquisition free columns",
                                            default={})
    process_free_cols: FreeColT = Field(title="Process free columns",
                                        default={})
    init_classif_list: List[int] = Field(title="Favorite taxa used in classification",
                                         default=[])

    managers: List[UserModel] = Field(title="Managers of this project",
                                      default=[])
    annotators: List[UserModel] = Field(title="Annotators of this project, if not manager",
                                        default=[])
    viewers: List[UserModel] = Field(title="Viewers of this project, if not manager nor annotator",
                                     default=[])
    contact: Optional[UserModel] = Field(title="The contact person is a manager who serves as the contact person for other users and EcoTaxa's managers.")

    highest_right: str = Field(
        title="The highest right for requester on this project. One of 'Manage', 'Annotate', 'View'.",
        default="")
    license: LicenseEnum = Field(title="Data licence",
                                 default=LicenseEnum.Copyright)

    # owner: UserModel = Field(title="Owner of this project")

    class Config:
        schema_extra = {
            "example": {
                "obj_free_cols": {"area": "n01", "esd": "n02"},
                "sample_free_cols": {"barcode": "t01"},
                "acquisition_free_cols": {"flash_delay": "t01"},
                "process_free_cols": {"nb_images": "t01"},
            }
        }


# TODO: when python 3.7+, we can have pydantic generics and remove the ignore below
class ProjectModel(_ProjectModelFromDB, _AddedToProject):  # type:ignore
    """
        Project + computed
    """


class SampleModel(_SampleModelFromDB):  # type:ignore
    free_columns: Dict[str, Any] = Field(title="Free columns from sample mapping in project",
                                         default={})


class AcquisitionModel(_AcquisitionModelFromDB):  # type:ignore
    free_columns: Dict[str, Any] = Field(title="Free columns from acquisition mapping in project",
                                         default={})


class ProcessModel(_ProcessModelFromDB):  # type:ignore
    free_columns: Dict[str, Any] = Field(title="Free columns from process mapping in project",
                                         default={})


class CreateProjectReq(BaseModel):
    clone_of_id: int = Field(title="If set, clone specified Project",
                             default=None)
    title: str = Field(title="The project title")
    visible: bool = Field(title="The project is created visible",
                          default=True)


class ProjectFilters(TypedDict, total=False):
    taxo: Optional[str]
    """ Coma-separated list of numeric taxonomy/category ids. Only include object classified with one of them """
    taxochild: Optional[str]
    """ If 'Y' and taxo is set, also include children of each member of 'taxo' list in taxonomy tree """
    statusfilter: Optional[str]
    """ Include objects with given status:
          'NV': Not validated 
          'PV': Predicted or Validated 
          'NVM': Validated, but not by me 
          'VM': Validated by me 
          'U': Not classified
           other: direct equality comparison with DB value """
    MapN: Optional[str]
    MapW: Optional[str]
    MapE: Optional[str]
    MapS: Optional[str]
    """ If all 4 are set, include objects inside the defined bounding rectangle. """
    depthmin: Optional[str]
    depthmax: Optional[str]
    """ If both are set, include objects for which both depths (min and max) are inside the range """
    samples: Optional[str]
    """ Coma-separated list of sample IDs, include only objects for these samples """
    instrum: Optional[str]
    """ Instrument name, include objects for which sampling was done using this instrument """
    daytime: Optional[str]
    """ Coma-separated list of sun position values: 
         D for Day, U for Dusk, N for Night, A for Dawn (Aube in French) """
    month: Optional[str]
    """ Coma-separated list of month numbers, 1=Jan and so on """
    fromdate: Optional[str]
    """ Format is 'YYYY-MM-DD', include objects collected after this date """
    todate: Optional[str]
    """ Format is 'YYYY-MM-DD', include objects collected before this date """
    fromtime: Optional[str]
    """ Format is 'HH24:MM:SS', include objects collected after this time of day """
    totime: Optional[str]
    """ Format is 'HH24:MM:SS', include objects collected before this time of day """
    inverttime: Optional[str]
    """ If '1', include objects outside fromtime an totime range """
    validfromdate: Optional[str]
    """ Format is 'YYYY-MM-DD HH24:MI', include objects validated after this date+time """
    validtodate: Optional[str]
    """ Format is 'YYYY-MM-DD HH24:MI', include objects validated before this date+time """
    freenum: Optional[str]
    """ Numerical DB column number in Object as basis for the 2 following criteria """
    freenumst: Optional[str]
    """ Start of included range for the column defined by freenum, in which objects are included """
    freenumend: Optional[str]
    """ End of included range for the column defined by freenum, in which objects are included """
    freetxt: Optional[str]
    """ Textual DB column number as basis for following criteria 
            If starts with 's' then it's a text column in Sample
            If starts with 'a' then it's a text column in Acquisition 
            If starts with 'p' then it's a text column in Process 
            If starts with 'o' then it's a text column in Object 
        """
    freetxtval: Optional[str]
    """ Text to match in the column defined by freetxt, for an object to be included """
    filt_annot: Optional[str]
    """ Coma-separated list of annotator, i.e. person who validated the classification
        at any point in time. """
    filt_last_annot: Optional[str]
    """ Coma-separated list of annotator, i.e. person who validated the classification
        in last. """


ProjectFiltersModel = typed_dict_to_model(ProjectFilters)


class ColUpdate(TypedDict):
    ucol: str
    """ A column name, pseudo-columns AKA free ones, are OK """
    uval: str
    """ The new value to set, always as a string """


class ColUpdateList(list):
    """
        Formalized way of updating entities in the system.
            It's, on purpose, not a Dict as we take provision for futures usage when we need an order.
    """

    def __init__(self, iterable: Iterable[ColUpdate]):
        super().__init__(iterable)

    def as_dict_for_db(self):
        ret = {}
        an_update: ColUpdate
        for an_update in self:
            upd_col = an_update["ucol"]
            ret[upd_col] = an_update["uval"]
            if ret[upd_col] == 'current_timestamp':
                ret[upd_col] = current_timestamp()
        return ret


class BulkUpdateReq(BaseModel):
    # TODO: A Union of possible types?
    target_ids: List[int] = Field(title="The IDs of the target entities")
    updates: ColUpdateList = Field(title="The updates, to do on all impacted entities")


# TODO: Derive from ProjectStats
class ProjectStatsModel(BaseModel):
    projid: int = Field(title="The project id")
    used_taxa: List[int] = Field(title="The taxa/category ids used inside the project", default=[])
    nb_unclassified: int = Field(title="The number of unclassified objects inside the project")
    nb_validated: int = Field(title="The number of validated objects inside the project")
    nb_dubious: int = Field(title="The number of dubious objects inside the project")
    nb_predicted: int = Field(title="The number of predicted objects inside the project")


class CreateCollectionReq(BaseModel):
    title: str = Field(title="The collection title")
    project_ids: List[int] = Field(title="The composing project IDs", min_items=1)


class _AddedToCollection(BaseModel):
    """
        What's added to Collection comparing to the plain DB record.
    """
    project_ids: List[int] = Field(title="The composing project IDs", min_items=1)
    provider_user: Optional[UserModel] = Field(title="""Is the person Person who is responsible for the content of this metadata record. 
Writer of the title and abstract.""")
    contact_user: Optional[UserModel] = Field(title="""Is the person who should be contacted in cases of questions regarding the
content of the dataset or any data restrictions. This is also the person who is most likely to
stay involved in the dataset the longest.""")
    creator_users: List[UserModel] = Field(title="""All people who are responsible for the creation of
the collection. Data creators should receive credit for their work and should therefore be
included in the citation.""",
                                           default=[])
    creator_organisations: List[str] = Field(title="""All organisations who are responsible for the creation of
    the collection. Data creators should receive credit for their work and should therefore be
    included in the citation.""",
                                             default=[])
    associate_users: List[UserModel] = Field(title="Other person(s) associated with the collection",
                                             default=[])
    associate_organisations: List[str] = Field(title="Other organisation(s) associated with the collection",
                                               default=[])


class CollectionModel(_CollectionModelFromDB, _AddedToCollection):  # type:ignore
    """
        Collection + computed
    """
