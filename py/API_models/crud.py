# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in CRUD API_operations.
#
from typing import Optional, Dict, Type, List, Any

from typing_extensions import TypedDict

from BO.ColumnUpdate import ColUpdateList
from BO.DataLicense import LicenseEnum
from BO.Project import ProjectUserStats
from BO.Sample import SampleTaxoStats
from DB import User, Project, Sample, Acquisition, Process, Job
from DB.Acquisition import ACQUISITION_FREE_COLUMNS
from DB.Collection import Collection
from DB.Process import PROCESS_FREE_COLUMNS
from DB.Sample import SAMPLE_FREE_COLUMNS
from helpers.pydantic import BaseModel, Field
from .helpers.DBtoModel import sqlalchemy_to_pydantic
from .helpers.DataclassToModel import dataclass_to_model
from .helpers.TypedDictToModel import typed_dict_to_model

# Enriched model
FreeColT = Dict[str, str]

# Direct mirror of DB models
_DBUserDescription = {
    "id": Field(title="Id", description="Unique user identifier", default=None, example=1),
    "email": Field(title="Email", description="User's email used during registration", default=None,
                   example="user@email.com"),
    "name": Field(title="Name", description="User's full name", default=None, example="userName"),
    "organisation": Field(title="Organisation", description="User's organisation", default=None,
                          example="Oceanographic Laboratory of Villefranche sur Mer - LOV"),
    "active": Field(title="Account status", description="User's Account status", default=None, example=True),
    "country": Field(title="Country", description="User's country", default=None, example="France"),
    "usercreationdate": Field(title="User creation date", description="User account creation date", default=None,
                              example="2020-11-05T12:31:48.299713"),
    "usercreationreason": Field(title="User creation reason",
                                description="The reason of creation of this user account",
                                default=None, example="Analysis of size and shapes of plastic particles")
}
_UserModelFromDB = sqlalchemy_to_pydantic(User, exclude=[User.password.name,
                                                         User.preferences.name,
                                                         User.mail_status.name,
                                                         User.mail_status_date.name], field_infos=_DBUserDescription)
_DBProjectDescription = {
    "projid": Field(title="Project Id", description="The project Id", example=4824),
    "title": Field(title="Title", description="The project title", example="MyProject"),
    "visible": Field(title="Visible", description="The project visibility", example=False),
    "status": Field(title="Status", description="The project status", example="Annotate"),
    "objcount": Field(title="Object count", description="The number of objects", example=32292.0),
    "pctvalidated": Field(title="Percentage validated", description="Percentage of validated images.",
                          example=0.015483711135885049),
    "pctclassified": Field(title="Percentage classified", description="Percentage of classified images.",
                           example=100.0),
    "classifsettings": Field(title="Classification settings", description="",
                             example="baseproject=1602\ncritvar=%area,angle,area,area_exc,bx,by,cdexc,centroids,circ.,circex,convarea,convperim,cv,elongation,esd,fcons,feret,feretareaexc,fractal,height,histcum1,histcum2,histcum3,intden,kurt,lat_end,lon_end,major,max,mean,meanpos,median,min,minor,mode,nb1,nb2,perim.,perimareaexc,perimferet,perimmajor,range,skelarea,skew,slope,sr,stddev,symetrieh,symetriehc,symetriev,symetrievc,thickr,width,x,xm,xstart,y,ym,ystart\nposttaxomapping=\nseltaxo=45074,84963,61990,13333,82399,61973,62005,25930,25932,61996,78426,81941,11514,85076,85061,30815,85185,92230,85079,84993,25824,85115,85004,26525,25944,11509,26524,92112,84976,25942,84980,85078,78418,84977,85060,61993,61991,85069,81871,74144,11758,72431,13381,11518,5,18758,85117,92042,84968,84997,87826,92236,92237,92039,84989,85193,83281,78412,92239,71617,81977,45071,12865,85044,81940,85067,12908,85116,56693,85008,92139,92068\nusemodel_foldername=testln1"),
    "classiffieldlist": Field(title="Classification field list", description="",
                              example="depth_min=depth_min\r\ndepth_max=depth_max\r\narea=area [pixel]\r\nmean=mean [0-255]\r\nfractal=fractal\r\nmajor=major [pixel]\r\nsymetrieh=symetrieh\r\ncirc.=circ\r\nferet = Feret [pixel]"),
    "popoverfieldlist": Field(title="Pop over field list", description="",
                              example="depth_min=depth_min\r\ndepth_max=depth_max\r\narea=area [pixel]\r\nmean=mean [0-255]\r\nfractal=fractal\r\nmajor=major [pixel]\r\nsymetrieh=symetrieh\r\ncirc.=circ\r\nferet = Feret [pixel]"),
    "comments": Field(title="Comments", description="The project comments", example=""),
    "description": Field(title="Description", description="The project description, i.e. main traits", example=""),
    "rf_models_used": Field(title="Rf models used", description="", example=""),
    "cnn_network_id": Field(title="Cnn network id", description="", example="SCN_zooscan_group1")
}
_ProjectModelFromDB: Type = sqlalchemy_to_pydantic(Project, exclude=[Project.mappingobj.name,
                                                                     Project.mappingacq.name,
                                                                     Project.mappingprocess.name,
                                                                     Project.mappingsample.name,
                                                                     Project.initclassiflist.name,
                                                                     ] + [
                                                                        # Not replaced yet but LOTS of data
                                                                        Project.fileloaded.name
                                                                    ], field_infos=_DBProjectDescription)


class ProjectSummaryModel(BaseModel):
    projid: int = Field(title="Project Id", description="Project unique identifier", default=None, example=1)
    title: str = Field(title="Project title", description="Project's title", default=None, example="Zooscan Tara Med")


# We exclude free columns from base model, they will be mapped in a dedicated sub-entity
_DBSampleDescription = {
    "sampleid": Field(title="Sample Id", description="The sample Id", example=100),
    "projid": Field(title="Project Id", description="The project Id", example=4),
    "orig_id": Field(title="Origine Id", description="The origine Id", example="dewex_leg2_19"),
    "latitude": Field(title="Latitude", description="The latitude", example=42.0231666666667),
    "longitude": Field(title="Longitude", description="The longitude", example=4.71766666666667),
    "dataportal_descriptor": Field(title="Dataportal descriptor", description="", example=""),

}
_SampleModelFromDB = sqlalchemy_to_pydantic(Sample,
                                            exclude=["t%02d" % i for i in range(1, SAMPLE_FREE_COLUMNS)],
                                            field_infos=_DBSampleDescription)
_DBAcquisitionDescription = {
    "acquisid": Field(title="Acquisition Id", description="The acquisition Id", example=144, default=None),
    "acq_sample_id": Field(title="Acquisition sample Id", description="The acquisition sample Id", example=1039,
                           default=None),
    "orig_id": Field(title="Origin Id", description="The origin Id", example="uvp5_station1_cast1b", default=None),
    "instrument": Field(title="Instrument", description="Instrument used", example="uvp5", default=None),

}
_AcquisitionModelFromDB = sqlalchemy_to_pydantic(Acquisition,
                                                 exclude=["t%02d" % i for i in range(1, ACQUISITION_FREE_COLUMNS)],
                                                 field_infos=_DBAcquisitionDescription)
# _DBProcessDescription = {
#     # TODO
# }
_ProcessModelFromDB = sqlalchemy_to_pydantic(Process,
                                             exclude=["t%02d" % i for i in range(1, PROCESS_FREE_COLUMNS)])
_DBCollectionDescription = {
    "id": Field(title="Id", description="The collection Id", default=None, example=1),
    "external_id": Field(title="External Id", description="The external Id", default=None, example=""),
    "external_id_system": Field(title="External id system", description="The external Id system", default=None,
                                example=""),
    "title": Field(title="Title", description="The collection title", default=None, example="My collection"),
    "short_title": Field(title="Short title", description="The collection short title", default=None,
                         example="My coll"),
    "citation": Field(title="Citation", description="The collection citation", default=None, example=""),
    "license": Field(title="License", description="The collection license", default=None, example=LicenseEnum.CC_BY),
    "abstract": Field(title="Abstract", description="The collection abstract", default=None, example=""),
    "description": Field(title="Description", description="The collection description", default=None, example=""),

}
_CollectionModelFromDB = sqlalchemy_to_pydantic(Collection,
                                                exclude=[Collection.contact_user_id.name,
                                                         Collection.provider_user_id.name],
                                                field_infos=_DBCollectionDescription)


class UserModel(_UserModelFromDB):  # type:ignore
    pass


class UserModelWithRights(UserModel):  # type:ignore
    can_do: List[int] = Field(title="User's permissions",
                              description="List of User's allowed actions : 1 create a project, 2 administrate the app, 3 administrate users, 4 create taxon",
                              default=[], example=[1, 4])
    last_used_projects: List[ProjectSummaryModel] = Field(title="Last used projects",
                                                          description="List of User's last used projects", default=[],
                                                          example=[
                                                              {
                                                                  "projid": 3,
                                                                  "title": "Zooscan point B"
                                                              },
                                                              {
                                                                  "projid": 1,
                                                                  "title": "Zooscan Tara Med"
                                                              }
                                                          ])


class _AddedToProject(BaseModel):
    obj_free_cols: FreeColT = Field(title="Object free cols", description="Object free columns", default={},
                                    example={"area": "n01", "esd": "n02"})
    sample_free_cols: FreeColT = Field(title="Sample free cols", description="Sample free columns", default={},
                                       example={"barcode": "t01"})
    acquisition_free_cols: FreeColT = Field(title="Acquisition free cols", description="Acquisition free columns",
                                            default={}, example={"flash_delay": "t01"})
    process_free_cols: FreeColT = Field(title="Process free cols", description="Process free columns", default={},
                                        example={"nb_images": "t01"})
    init_classif_list: List[int] = Field(title="Init classification list",
                                         description="Favorite taxa used in classification", default=[],
                                         example=[5, 11493, 11498, 11509])

    managers: List[UserModel] = Field(title="Managers", description="Managers of this project", default=[])
    annotators: List[UserModel] = Field(title="Annotators", description="Annotators of this project, if not manager",
                                        default=[])
    viewers: List[UserModel] = Field(title="Viewers",
                                     description="Viewers of this project, if not manager nor annotator", default=[])
    instrument: Optional[str] = Field(title="Instrument",
                                      description="This project's instrument. Transitory: if several of them, then coma-separated",
                                      example="zooscan")
    contact: Optional[UserModel] = Field(title="Contact",
                                         description="The contact person is a manager who serves as the contact person for other users and EcoTaxa's managers.")

    highest_right: str = Field(title="Highest right",
                               description="The highest right for requester on this project. One of 'Manage', 'Annotate', 'View'.",
                               default="", example="View")
    license: LicenseEnum = Field(title="License", description="Data licence", default=LicenseEnum.Copyright,
                                 example=LicenseEnum.CC_BY)

    # owner: UserModel = Field(title="Owner of this project")


# TODO: when python 3.7+, we can have pydantic generics and remove the ignore below
class ProjectModel(_ProjectModelFromDB, _AddedToProject):  # type:ignore
    """
        Project + computed
    """


class SampleModel(_SampleModelFromDB):  # type:ignore
    free_columns: Dict[str, Any] = Field(title="Free columns",
                                         description="Free columns from sample mapping in project",
                                         default={}, example={"flash_delay": "t01"})


SampleTaxoStatsModel = dataclass_to_model(SampleTaxoStats, add_suffix=True,
                                          titles={'sample_id': "Sample id",
                                                  'used_taxa': "Used taxa",
                                                  "nb_unclassified": "Number unclassified",
                                                  "nb_validated": "Number validated",
                                                  "nb_dubious": "Number dubious",
                                                  "nb_predicted": "Number predicted"
                                                  },
                                          descriptions={'sample_id': "The sample id",
                                                        'used_taxa': "The taxa/category ids used inside the sample. -1 for unclassified objects",
                                                        "nb_unclassified": "The number of unclassified objects inside the sample",
                                                        "nb_validated": "The number of validated objects inside the sample",
                                                        "nb_dubious": "The number of dubious objects inside the sample",
                                                        "nb_predicted": "The number of predicted objects inside the sample"
                                                        })


class AcquisitionModel(_AcquisitionModelFromDB):  # type:ignore
    free_columns: Dict[str, Any] = Field(title="Free columns",
                                         description="Free columns from acquisition mapping in project",
                                         default={}, example={"bottomdepth": 322, "ship": "suroit"})


class ProcessModel(_ProcessModelFromDB):  # type:ignore
    free_columns: Dict[str, Any] = Field(title="Free columns from process mapping in project",
                                         default={})


class CreateProjectReq(BaseModel):
    clone_of_id: int = Field(title="Clone of id", description="If set, clone specified Project", default=None,
                             example=2)
    title: str = Field(title="Title", description="The project title", example="My new project title")
    visible: bool = Field(title="Visible", description="If True, the project is created visible", default=True,
                          example=True)


class ProjectFilters(TypedDict, total=False):
    taxo: Optional[str]
    """ Coma-separated list of numeric taxonomy/category ids. Only include objects classified with one of them """
    taxochild: Optional[str]
    """ If 'Y' and taxo is set, also include children of each member of 'taxo' list in taxonomy tree """
    statusfilter: Optional[str]
    """ Include objects with given status:
          'NV': Not validated 
          'PV': Predicted or Validated 
          'PVD': Predicted or Validated or Dubious
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
    """ Format is 'YYYY-MM-DD HH24:MI', include objects validated/set to dubious after this date+time """
    validtodate: Optional[str]
    """ Format is 'YYYY-MM-DD HH24:MI', include objects validated/set to dubious before this date+time """
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


class BulkUpdateReq(BaseModel):
    # TODO: A Union of possible types?
    target_ids: List[int] = Field(title="Target Id", description="The IDs of the target entities", example=[1, 5, 290])
    updates: ColUpdateList = Field(title="Updates", description="The list of updates, to do on all impacted entities. \n\n \
    { \n\n \
        ucol : A column name, pseudo-columns AKA free ones, are OK. \n\n \
        uval : The new value to set, always as a string \n\n \
    }",
                                   example=[{"ucol": "sub_part", "uval": "2"}])
    # updates: List[ColUpdate] = Field(title="Updates", description="The updates, to do on all impacted entities") 


# TODO: Derive from ProjectTaxoStats
class ProjectTaxoStatsModel(BaseModel):
    projid: int = Field(title="projid", description="The project id", example=1)
    used_taxa: List[int] = Field(title="used_taxa", description="The taxa/category ids used inside the project."
                                                                " An id of -1 means some unclassified objects",
                                 default=[], example=[45072, 78418, 84963, 85011, 85012, 85078])
    nb_unclassified: int = Field(title="nb_unclassified",
                                 description="The number of unclassified objects inside the project", example=0)
    nb_validated: int = Field(title="nb_validated", description="The number of validated objects inside the project",
                              example=5000)
    nb_dubious: int = Field(title="nb_dubious", description="The number of dubious objects inside the project",
                            example=56)
    nb_predicted: int = Field(title="nb_predicted", description="The number of predicted objects inside the project",
                              example=1345)


ProjectUserStatsModel = dataclass_to_model(ProjectUserStats, add_suffix=True,
                                           titles={'projid': "Project id",
                                                   'annotators': "Annotators",
                                                   'activities': "Activities"},
                                           descriptions={
                                               'projid': "The project id",
                                               'annotators': "The users who ever decided on classification or state of objects",
                                               'activities': "More details on annotators' activities"
                                           })


class CreateCollectionReq(BaseModel):
    title: str = Field(title="Title", description="The collection title",
                       example="My collection")
    project_ids: List[int] = Field(title="Project ids", description="The list of composing project IDs",
                                   example=[1], min_items=1)


class _AddedToCollection(BaseModel):
    """
        What's added to Collection comparing to the plain DB record.
    """
    project_ids: List[int] = Field(title="Project ids", description="The list of composing project IDs",
                                   example=[1], min_items=1)
    provider_user: Optional[UserModel] = Field(title="Provider user", description="""Is the person who 
        is responsible for the content of this metadata record. Writer of the title and abstract.""")
    contact_user: Optional[UserModel] = Field(title="Contact user", description="""Is the person who 
        should be contacted in cases of questions regarding the content of the dataset or any data restrictions. 
        This is also the person who is most likely to stay involved in the dataset the longest.""")
    creator_users: List[UserModel] = Field(title="Creator users", description="""All people who 
        are responsible for the creation of the collection. Data creators should receive credit 
        for their work and should therefore be included in the citation.""", default=[])
    creator_organisations: List[str] = Field(title="Creator organisations", description="""All 
        organisations who are responsible for the creation of the collection. Data creators should 
        receive credit for their work and should therefore be included in the citation.""", default=[])
    associate_users: List[UserModel] = Field(title="Associate users", description="""Other person(s) 
        associated with the collection""", default=[])
    associate_organisations: List[str] = Field(title="Associate organisations", description="""Other 
        organisation(s) associated with the collection""", default=[])


class CollectionModel(_CollectionModelFromDB, _AddedToCollection):  # type:ignore
    """
        Collection + computed
    """


_JobModelFromDB = sqlalchemy_to_pydantic(Job, exclude=[Job.params.name,
                                                       Job.result.name,
                                                       Job.messages.name,
                                                       Job.question.name,
                                                       Job.reply.name,
                                                       Job.inside.name])


class _AddedToJob(BaseModel):
    """
        What's added to a Job compared to the plain DB record.
    """
    params: Dict[str, Any] = Field(title="Creation parameters", default={})
    result: Dict[str, Any] = Field(title="Final result of the run", default={})
    errors: List[str] = Field(title="The errors seen during last step", default=[])
    question: Dict[str, Any] = Field(title="The data provoking job move to Asking state", default={})
    reply: Dict[str, Any] = Field(title="The data provided as a reply to the question", default={})
    inside: Dict[str, Any] = Field(title="Internal state of the job", default={})


class JobModel(_JobModelFromDB, _AddedToJob):  # type:ignore
    """
        All from DB table
    """
