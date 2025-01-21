# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in CRUD API_operations.
#
from typing import Optional, Dict, List, Any, Tuple, OrderedDict, Union
from BO.ColumnUpdate import ColUpdate
from BO.DataLicense import LicenseEnum, AccessLevelEnum
from BO.Job import DBJobStateEnum
from BO.Collection import OrganisationIDT
from BO.Project import ProjectUserStats, ProjectColumns
from BO.ProjectSet import ProjectSetColumnStats
from BO.Sample import SampleTaxoStats
from BO.User import UserIDT, UserIDListT
from DB.Acquisition import Acquisition
from DB.Collection import Collection
from DB.Instrument import UNKNOWN_INSTRUMENT
from DB.Job import Job
from DB.Process import Process
from DB.Project import Project, ProjectIDListT
from DB.Sample import Sample
from DB.User import User
from helpers.pydantic import BaseModel, Field, DescriptiveModel
from .helpers.DBtoModel import combine_models
from .helpers.DataclassToModel import dataclass_to_model_with_suffix

# Enriched model
FreeColT = Dict[str, str]


# Minimal user information
class _MinUserModel(DescriptiveModel):
    id = Field(title="Id", description="The unique numeric id of this user.", example=1)
    email = Field(
        title="Email",
        description="User's email address, as text, used during registration.",
        example="ecotaxa.api.user@gmail.com",
    )
    name = Field(
        title="Name", description="User's full name, as text.", example="userName"
    )


class _UserCollectionModel(_MinUserModel):
    orcid = Field(title="orcid", description="orcid unique identifier for this user")


MinUserModel = combine_models(User, _MinUserModel)
UserCollectionModel = combine_models(User, _UserCollectionModel)
# Direct mirror of DB models, i.e. the minimal + the rest we want
class _FullUserModel(_MinUserModel):
    organisation = Field(
        title="Organisation",
        description="User's organisation name, as text.",
        example="Oceanographic Laboratory of Villefranche sur Mer - LOV",
    )
    status = Field(
        default=1,
        title="Account status",
        description="Status of the user : 1 for active, 0 for inactive ,2 for pending, -1 for blocked",
        example=1,
    )
    status_date = Field(
        title="status date",
        description="Timestamp status modification date",
        example="2020-11-05T12:31:48.299713",
    )
    status_admin_comment = Field(
        title="Comment",
        description="Optional Users admininistrator comment about the account status.",
        example="",
    )
    country = Field(
        title="Country",
        description="The country name, as text (but chosen in a consistent list).",
        example="France",
    )
    orcid = Field(
        title="ORCID ID",
        description="The orcid id https://support.orcid.org.",
        example="0000-0001-2345-6789",
    )
    usercreationdate = Field(
        title="User creation date",
        description="The date of creation of the user, as text formatted according to the ISO 8601 standard.",
        example="2020-11-05T12:31:48.299713",
    )
    usercreationreason = Field(
        title="User creation reason",
        description="Paragraph describing the usage of EcoTaxa made by the user.",
        example="Analysis of size and shapes of plastic particles",
    )
    password = Field(
        title="User's password'",
        description="Encrypted (or not) password.",
        example="$foobar45$",
    )
    mail_status = Field(
        title="Mail status",
        description="True for verified, False for waiting for verification, None for no action.",
        example=True,
    )
    mail_status_date = Field(
        title="Mail status date",
        description="Timestamp mail status modification date",
        example="2020-11-05T12:31:48.299713",
    )


_UserModelFromDB = combine_models(User, _FullUserModel)

# TODO JCE - description example
class _Project2Model(DescriptiveModel):
    projid = Field(title="Project Id", description="The project Id.", example=4824)
    title = Field(title="Title", description="The project title.", example="MyProject")
    visible = Field(
        title="Visible", description="The project visibility.", example=False
    )
    status = Field(
        title="Status", description="The project status.", example="Annotate"
    )
    objcount = Field(
        title="Object count", description="The number of objects.", example=32292.0
    )
    pctvalidated = Field(
        title="Percentage validated",
        description="Percentage of validated images.",
        example=0.015483711135885049,
    )
    pctclassified = Field(
        title="Percentage classified",
        description="Percentage of classified images.",
        example=100.0,
    )
    classifsettings = Field(
        title="Classification settings",
        description="",
        example="baseproject=1602\ncritvar=%area,angle,area,area_exc,bx,by,cdexc,centroids,circ.,circex,convarea,convperim,cv,elongation,esd,fcons,feret,feretareaexc,fractal,height,histcum1,histcum2,histcum3,intden,kurt,lat_end,lon_end,major,max,mean,meanpos,median,min,minor,mode,nb1,nb2,perim.,perimareaexc,perimferet,perimmajor,range,skelarea,skew,slope,sr,stddev,symetrieh,symetriehc,symetriev,symetrievc,thickr,width,x,xm,xstart,y,ym,ystart\nposttaxomapping=\nseltaxo=45074,84963,61990,13333,82399,61973,62005,25930,25932,61996,78426,81941,11514,85076,85061,30815,85185,92230,85079,84993,25824,85115,85004,26525,25944,11509,26524,92112,84976,25942,84980,85078,78418,84977,85060,61993,61991,85069,81871,74144,11758,72431,13381,11518,5,18758,85117,92042,84968,84997,87826,92236,92237,92039,84989,85193,83281,78412,92239,71617,81977,45071,12865,85044,81940,85067,12908,85116,56693,85008,92139,92068\nusemodel_foldername=testln1",
    )
    classiffieldlist = Field(
        title="Classification field list",
        description="",
        example="depth_min=depth_min\r\ndepth_max=depth_max\r\narea=area [pixel]\r\nmean=mean [0-255]\r\nfractal=fractal\r\nmajor=major [pixel]\r\nsymetrieh=symetrieh\r\ncirc.=circ\r\nferet = Feret [pixel]",
    )
    popoverfieldlist = Field(
        title="Pop over field list",
        description="",
        example="depth_min=depth_min\r\ndepth_max=depth_max\r\narea=area [pixel]\r\nmean=mean [0-255]\r\nfractal=fractal\r\nmajor=major [pixel]\r\nsymetrieh=symetrieh\r\ncirc.=circ\r\nferet = Feret [pixel]",
    )
    comments = Field(title="Comments", description="The project comments.", example="")
    description = Field(
        title="Description",
        description="The project description, i.e. main traits.",
        example="",
    )
    rf_models_used = Field(title="Rf models used", description="", example="")
    cnn_network_id = Field(
        title="Cnn network id", description="", example="SCN_zooscan_group1"
    )


_ProjectModelFromDB = combine_models(Project, _Project2Model)


class ProjectSummaryModel(BaseModel):
    projid: int = Field(
        title="Project Id", description="Project unique identifier.", example=1
    )
    title: str = Field(
        title="Project title",
        description="Project's title.",
        example="Zooscan Tara Med",
    )


class UserModelWithRights(_UserModelFromDB):
    can_do: List[int] = Field(
        title="User's permissions",
        description="List of User's allowed actions : 1 create a project, 2 administrate the app, 3 administrate users, 4 create taxon.",
        default=[],
        example=[1, 4],
    )
    last_used_projects: List[ProjectSummaryModel] = Field(
        title="Last used projects",
        description="List of User's last used projects.",
        default=[],
        example=[
            {"projid": 3, "title": "Zooscan point B"},
            {"projid": 1, "title": "Zooscan Tara Med"},
        ],
    )


# TODO JCE - description example
# We exclude free columns from base model, they will be mapped in a dedicated sub-entity
class _Sample2Model(DescriptiveModel):
    sampleid = Field(title="Sample Id", description="The sample Id.", example=100)
    projid = Field(title="Project Id", description="The project Id.", example=4)
    orig_id = Field(
        title="Original id",
        description="Original sample ID from initial TSV load.",
        example="dewex_leg2_19",
    )
    latitude = Field(
        title="Latitude", description="The latitude.", example=42.0231666666667
    )
    longitude = Field(
        title="Longitude", description="The longitude.", example=4.71766666666667
    )
    dataportal_descriptor = Field(
        title="Dataportal descriptor.", description="", example=""
    )


_SampleModelFromDB = combine_models(Sample, _Sample2Model)


class _Acquisition2Model(DescriptiveModel):
    acquisid = Field(
        title="Acquisition Id", description="The acquisition Id.", example=144
    )
    acq_sample_id = Field(
        title="Acquisition sample Id",
        description="The acquisition sample Id.",
        example=1039,
    )
    orig_id = Field(
        title="Original id",
        description="Original acquisition ID from initial TSV load.",
        example="uvp5_station1_cast1b",
    )
    instrument = Field(
        title="Instrument", description="Instrument used.", example="uvp5"
    )


_AcquisitionModelFromDB = combine_models(Acquisition, _Acquisition2Model)


class _Process2Model(DescriptiveModel):
    processid = Field(title="Process id", description="The process Id.", example=1000)
    orig_id = Field(
        title="Original id",
        description="Original process ID from initial TSV load.",
        example="zooprocess_045",
    )


_ProcessModelFromDB = combine_models(Process, _Process2Model)


# TODO JCE - example
class _Collection2Model(DescriptiveModel):
    id = Field(title="Id", description="The collection Id.", example=1)
    external_id = Field(title="External Id", description="The external Id.", example="")
    external_id_system = Field(
        title="External id system", description="The external Id system.", example=""
    )
    title = Field(
        title="Title", description="The collection title.", example="My collection"
    )
    short_title = Field(
        title="Short title",
        description="The collection short title.",
        example="My coll",
    )
    citation = Field(
        title="Citation", description="The collection citation.", example=""
    )
    license = Field(
        title="License",
        description="The collection license.",
        example=LicenseEnum.CC_BY,
    )
    abstract = Field(
        title="Abstract", description="The collection abstract.", example=""
    )
    description = Field(
        title="Description", description="The collection description.", example=""
    )


_CollectionModelFromDB = combine_models(Collection, _Collection2Model)


class _AddedToProject(BaseModel):
    obj_free_cols: FreeColT = Field(
        title="Object free cols",
        description="Object free columns.",
        default={},
        example={"area": "n01", "esd": "n02"},
    )
    sample_free_cols: FreeColT = Field(
        title="Sample free cols",
        description="Sample free columns.",
        default={},
        example={"barcode": "t01"},
    )
    acquisition_free_cols: FreeColT = Field(
        title="Acquisition free cols",
        description="Acquisition free columns.",
        default={},
        example={"flash_delay": "t01"},
    )
    process_free_cols: FreeColT = Field(
        title="Process free cols",
        description="Process free columns.",
        default={},
        example={"nb_images": "t01"},
    )
    bodc_variables: Dict[str, Optional[str]] = Field(
        title="Expressions for computing standard BODC quantities.",
        description="BODC quantities from columns. Only the 3 keys listed in example are valid.",
        default={},
        example={
            "subsample_coef": "1/ssm.sub_part",
            "total_water_volume": "sam.tot_vol/1000",
            "individual_volume": "4.0/3.0*math.pi*(math.sqrt(obj.area/math.pi)*ssm.pixel_size)**3",
        },
    )
    init_classif_list: List[int] = Field(
        title="Init classification list",
        description="Favorite taxa used in classification.",
        default=[],
        example=[5, 11493, 11498, 11509],
    )

    managers: List[MinUserModel] = Field(
        title="Managers", description="Managers of this project.", default=[]
    )
    annotators: List[MinUserModel] = Field(
        title="Annotators",
        description="Annotators of this project, if not manager.",
        default=[],
    )
    viewers: List[MinUserModel] = Field(
        title="Viewers",
        description="Viewers of this project, if not manager nor annotator.",
        default=[],
    )
    instrument: Optional[str] = Field(
        title="Instrument",
        description="This project's instrument code.",
        example="Zooscan",
    )
    instrument_url: Optional[str] = Field(
        title="Instrument URL",
        description="This project's instrument BODC definition.",
        example="http://vocab.nerc.ac.uk/collection/L22/current/TOOL1581/",
    )
    contact: Optional[MinUserModel] = Field(
        title="Contact",
        description="The contact person is a manager who serves as the contact person for other users and EcoTaxa's managers.",
    )

    highest_right: str = Field(
        title="Highest right",
        description="The highest right for requester on this project. One of 'Manage', 'Annotate', 'View'.",
        default="",
        example="View",
    )
    license: LicenseEnum = Field(
        title="License",
        description="Data licence.",
        default=LicenseEnum.Copyright,
        example=LicenseEnum.CC_BY,
    )

    # owner: UserModel = Field(title="Owner of this project")


class ProjectModel(_ProjectModelFromDB, _AddedToProject):
    """
    Basic and computed information about the Project.
    """


class CollectionAggregatedRsp(BaseModel):
    """
    collection model extended with computed informations about the collection projects
    """

    can_be_administered: bool = Field(
        title="Can be administered",
        description="Whether the current user is manager of all collection projects",
        default=False,
    )
    instrument: str = Field(
        title="Instrument",
        description="The collection instrument from projects.",
        default=UNKNOWN_INSTRUMENT,
        example="UVP5",
    )
    access: str = Field(
        title="Access",
        description="The restricted access for collection projects.",
        example=AccessLevelEnum.OPEN,
        default=AccessLevelEnum.OPEN,
    )
    initclassiflist: str = Field(
        title="Initial categories",
        description=" Aggregated categories from the collection projects.",
    )
    classiffieldlist: str = Field(
        title="Sorting fields",
        description=" Aggregated sorting and displaying fields from the collection projects.",
    )
    cnn_network_id: str = Field(
        title="Deep Features",
        description=" Common deep features for the collection projects. Can be None (???)",
    )
    status: str = Field(
        title="Status",
        description=" the restricted collection status calculated from projects.",
    )
    creator_users: List[UserCollectionModel] = Field(
        title="Creator users",
        description="""Annotators extracted from history.""",
        default=[],
    )
    privileges: Dict[str, List[UserCollectionModel]] = Field(
        title="privileges",
        description="Aggregated user privileges of projects with user minimal right on projects",
        example={
            "managers": [],
            "annotators": [],
            "viewers": [],
        },
        default={"managers": [], "annotators": [], "viewers": []},
    )
    freecols: Dict[str, Dict[str, str]] = Field(
        title="freecols",
        description="Common free cols of projects.",
        default={},
        example={
            "mappingobj": {"n01": "annotation_confidencepmax"},
            "mappingsample": {"t01": "cruise", "t02": "vessel", "t03": "barcode"},
            "mappingprocess": {},
            "mappingacq": {},
        },
    )
    excluded: Dict[str, ProjectIDListT] = Field(
        title="excluded",
        default={},
        description="Excluded projects for common values ",
        example={"status": [1, 5, 12], "access": [1]},
    )


class SampleModel(_SampleModelFromDB):
    free_columns: Dict[str, Any] = Field(
        title="Free columns",
        description="Free columns from sample mapping in project.",
        default={},
        example={"flash_delay": "t01"},
    )


class _DBSampleTaxoStatsDescription(DescriptiveModel):
    sample_id = Field(title="Sample id", description="The sample id.")
    used_taxa = Field(
        title="Used taxa",
        description="The taxa/category ids used inside the sample. -1 for unclassified objects.",
    )
    nb_unclassified = Field(
        title="Number unclassified",
        description="The number of unclassified objects inside the sample.",
    )
    nb_validated = Field(
        title="Number validated",
        description="The number of validated objects inside the sample.",
    )
    nb_dubious = Field(
        title="Number dubious",
        description="The number of dubious objects inside the sample.",
    )
    nb_predicted = Field(
        title="Number predicted",
        description="The number of predicted objects inside the sample.",
    )


SampleTaxoStatsModel = dataclass_to_model_with_suffix(
    SampleTaxoStats, _DBSampleTaxoStatsDescription
)


class AcquisitionModel(_AcquisitionModelFromDB):
    free_columns: Dict[str, Any] = Field(
        title="Free columns",
        description="Free columns from acquisition mapping in project.",
        default={},
        example={"bottomdepth": 322, "ship": "suroit"},
    )


class ProcessModel(_ProcessModelFromDB):
    free_columns: Dict[str, Any] = Field(
        title="Free columns from process mapping in project",
        default={},
        example={
            "software": "zooprocess_pid_to_ecotaxa_7.26_2017/12/19",
            "pressure_gain": "10",
        },
    )


class CreateProjectReq(BaseModel):
    clone_of_id: Optional[int] = Field(
        title="Clone of id",
        description="Internal, numeric id of a project to clone as a new one. By default it does not clone anything.",
        default=None,
        example=2,
    )
    title: str = Field(
        title="Title",
        description="The project title, as text.",
        example="My new project title",
    )
    instrument: str = Field(
        title="Instrument",
        description="The project instrument.",
        default=UNKNOWN_INSTRUMENT,
        example="UVP5",
    )
    visible: bool = Field(
        title="Visible",
        description="When TRUE, the project is created visible by all users.",
        default=True,
        example=True,
    )

    class Config:
        schema_extra = {"title": "Create project request Model"}


class BulkUpdateReq(BaseModel):
    target_ids: List[int] = Field(
        title="Target Id",
        description="The IDs of the target entities.",
        example=[1, 5, 290],
    )
    updates: List[ColUpdate] = Field(
        title="Updates",
        description="The list of updates, to do on all impacted entities. \n\n \
    { \n\n \
        ucol : A column name, pseudo-columns AKA free ones, are OK. \n\n \
        uval : The new value to set, always as a string \n\n \
    }",
        example=[{"ucol": "sub_part", "uval": "2"}],
    )

    class Config:
        schema_extra = {"title": "Update request Model"}


# TODO: Derive from ProjectTaxoStats
class ProjectTaxoStatsModel(BaseModel):
    projid: int = Field(title="projid", description="The project id.", example=1)
    used_taxa: List[int] = Field(
        title="used_taxa",
        description="The taxa/category ids used inside the project."
        " An id of -1 means some unclassified objects.",
        default=[],
        example=[45072, 78418, 84963, 85011, 85012, 85078],
    )
    nb_unclassified: int = Field(
        title="nb_unclassified",
        description="The number of unclassified objects inside the project.",
        example=0,
    )
    nb_validated: int = Field(
        title="nb_validated",
        description="The number of validated objects inside the project.",
        example=5000,
    )
    nb_dubious: int = Field(
        title="nb_dubious",
        description="The number of dubious objects inside the project.",
        example=56,
    )
    nb_predicted: int = Field(
        title="nb_predicted",
        description="The number of predicted objects inside the project.",
        example=1345,
    )


class _DBProjectUserStatsDescription(DescriptiveModel):
    projid = Field(title="Project id", description="The project id.")
    annotators = Field(
        title="Annotators",
        description="The users who ever decided on classification or state of objects.",
    )
    activities = Field(
        title="Activities", description="More details on annotators' activities."
    )


ProjectUserStatsModel = dataclass_to_model_with_suffix(
    ProjectUserStats, _DBProjectUserStatsDescription
)


class _DBProjectSetColumnStatDescription(DescriptiveModel):
    proj_ids = Field(title="Projects IDs", description="Projects IDs from the call.")
    columns = Field(title="Columns", description="Column names from the call.")
    total = Field(
        title="Total of rows", description="All rows regardless of emptiness."
    )
    counts = Field(
        title="Counts", description="Counts of non-empty values, one per column."
    )
    variances = Field(
        title="Variances", description="Variances of values, one per column."
    )


ProjectSetColumnStatsModel = dataclass_to_model_with_suffix(
    ProjectSetColumnStats, _DBProjectSetColumnStatDescription
)


class _ProjectColumnsDescription(DescriptiveModel):
    projid = Field(title="Project ID", description="Project ID from the call.")
    columns = Field(title="Columns", description="Column names from the call.")
    values = Field(title="All rows", description="All rows regardless of emptiness.")


ProjectColumnsModel = dataclass_to_model_with_suffix(
    ProjectColumns, _ProjectColumnsDescription
)


class CreateCollectionReq(BaseModel):
    title: str = Field(
        title="Title", description="The collection title.", example="My collection"
    )
    project_ids: List[int] = Field(
        title="Project ids",
        description="The list of composing project IDs.",
        example=[1],
        min_items=1,
    )

    class Config:
        schema_extra = {"title": "Create collection request Model"}


class _AddedToCollection(BaseModel):
    """
    What's added to Collection comparing to the plain DB record.
    """

    project_ids: List[int] = Field(
        title="Project ids",
        description="The list of composing project IDs.",
        example=[1],
        min_items=1,
    )
    provider_user: Optional[MinUserModel] = Field(
        title="Provider user",
        description="""Is the person who
        is responsible for the content of this metadata record. Writer of the title and abstract.""",
    )
    contact_user: Optional[MinUserModel] = Field(
        title="Contact user",
        description="""Is the person who
        should be contacted in cases of questions regarding the content of the dataset or any data restrictions.
        This is also the person who is most likely to stay involved in the dataset the longest.""",
    )
    creator_users: List[MinUserModel] = Field(
        title="Creator users",
        description="""All people who
        are responsible for the creation of the collection. Data creators should receive credit
        for their work and should therefore be included in the citation.""",
        default=[],
    )
    creator_organisations: List[str] = Field(
        title="Creator organisations",
        description="""All
        organisations who are responsible for the creation of the collection. Data creators should
        receive credit for their work and should therefore be included in the citation.""",
        default=[],
    )
    associate_users: List[MinUserModel] = Field(
        title="Associate users",
        description="""Other person(s)
        associated with the collection.""",
        default=[],
    )
    associate_organisations: List[str] = Field(
        title="Associate organisations",
        description="""Other
        organisation(s) associated with the collection.""",
        default=[],
    )


class CollectionModel(_CollectionModelFromDB, _AddedToCollection):
    """
    Basic and computed information about the Collection.
    """

    class Config:
        schema_extra = {"title": "Collection Model"}


class CollectionReq(BaseModel):
    """
    update full or partial collection Request model
    """

    external_id: Union[str, None] = Field(
        title="External Id", description="The external Id.", example=""
    )
    title: Union[str, None] = Field(
        title="Title", description="The collection title.", example="My collection"
    )
    short_title: Union[str, None] = Field(
        title="Short title",
        description="The collection short title.",
        example="My coll",
    )
    provider_user_id: Union[UserIDT, None] = Field(
        title="Provider user Id",
        description="""Id of the person who
        is responsible for the content of this metadata record. Writer of the title and abstract.""",
    )
    contact_user_id: Union[UserIDT, None] = Field(
        title="Contact user Id",
        description="""Id of the person who
        should be contacted in cases of questions regarding the content of the dataset or any data restrictions.
        This is also the person who is most likely to stay involved in the dataset the longest.""",
    )
    project_ids: Union[ProjectIDListT, None] = Field(
        title="Project ids",
        description="The list of composing project IDs.",
        example=[1],
        min_items=1,
    )
    license: Union[LicenseEnum, None] = Field(
        title="License",
        description="The collection license.",
        example=LicenseEnum.CC_BY,
    )
    citation: Union[str, None] = Field(
        title="Citation", description="The collection citation.", example=""
    )
    abstract: Union[str, None] = Field(
        title="Abstract", description="The collection abstract.", example=""
    )
    description: Union[str, None] = Field(
        title="Description", description="The collection description.", example=""
    )
    creator_users: Union[List[Union[UserIDT, Any]], None] = Field(
        title="Creator users Ids",
        description="""List of users id's or dict with name, organization for external persons.""",
    )
    associate_users: Union[List[Union[UserIDT, Any]], None] = Field(
        title="Associate users",
        description="""List of users id's or dict with name, organization for external persons.""",
    )
    creator_organisations: Union[List[Union[OrganisationIDT, Any]], None] = Field(
        title="Creator organisations Ids or names",
        description="""All
        organisations who are responsible for the creation of the collection. Data creators should
        receive credit for their work and should therefore be included in the citation.""",
    )
    associate_organisations: Union[List[Union[OrganisationIDT, Any]], None] = Field(
        title="Associate organisations",
        description="""Other
        organisation(s) Ids or names associated with the collection.""",
    )

    class Config:
        schema_extra = {"title": "Update full or partial Collection Model"}


class _Job2Model(DescriptiveModel):
    id = Field(title="id", description="Job unique identifier.", example=47445)
    owner_id = Field(
        title="owner_id",
        description="The user who created and thus owns the job. ",
        example=1,
    )
    type = Field(
        title="type",
        description="The job type, e.g. import, export... ",
        example="Subset",
    )
    state = Field(
        title="state",
        description="What the job is doing. Could be 'P' for Pending (Waiting for an execution thread), 'R' for Running (Being executed inside a thread), 'A' for Asking (Needing user information before resuming), 'E' for Error (Stopped with error), 'F' for Finished (Done).",
        example=DBJobStateEnum.Finished,
    )
    step = Field(
        title="step", description="Where in the workflow the job is. ", example="null"
    )
    progress_pct = Field(
        title="progress_pct",
        description="The progress percentage for UI. ",
        example=100,
    )
    progress_msg = Field(
        title="progress_msg",
        description="The message for UI, short version. ",
        example="Done",
    )
    creation_date = Field(
        title="creation_date",
        description="The date of creation of the Job, as text formatted according to the ISO 8601 standard.",
        example="2021-09-28T08:43:20.196061",
    )
    updated_on = Field(
        title="updated_on",
        description="Last time that anything changed in present line. ",
        example="2021-09-28T08:43:21.441969",
    )


_JobModelFromDB = combine_models(Job, _Job2Model)


class _AddedToJob(BaseModel):
    """
    What's added to a Job compared to the plain DB record.
    """

    params: Dict[str, Any] = Field(
        title="params",
        description="Creation parameters.",
        default={},
        example={
            "prj_id": 1,
            "req": {
                "filters": {"taxo": "85067", "taxochild": "N"},
                "dest_prj_id": 1,
                "group_type": "S",
                "limit_type": "P",
                "limit_value": 100.0,
                "do_images": True,
            },
        },
    )
    result: Dict[str, Any] = Field(
        title="result",
        description="Final result of the run.",
        default={},
        example={"rowcount": 3},
    )
    errors: List[str] = Field(
        title="errors",
        description="The errors seen during last step.",
        default=[],
        example=[],
    )
    question: Dict[str, Any] = Field(
        title="question",
        description="The data provoking job move to Asking state.",
        default={},
        example={},
    )
    reply: Dict[str, Any] = Field(
        title="reply",
        description="The data provided as a reply to the question.",
        default={},
        example={},
    )
    inside: Dict[str, Any] = Field(
        title="inside", description="Internal state of the job.", default={}, example={}
    )


class JobModel(_JobModelFromDB, _AddedToJob):
    """
    All information about the Job.
    """


class ResetPasswordReq(BaseModel):
    """
    Minimal user information need to reset the password
    """

    id: int = Field(
        title="User Id",
        description="User unique identifier.",
        example=1,
        default=-1,
    )
    email: Optional[str] = Field(title="Email", default=None)
    password: Optional[str] = Field(title="Password", default=None)


class UserActivateReq(BaseModel):
    """
    Request to modify status of a user by a Users Administrator or confirm email_status, or resend emails (when token is expired) to confirm email or modify pending profile by a user.
    """

    token: Optional[str] = Field(
        default=None,
        title="token",
        description="token when the user is not an admin and must confirm the email. ",
    )
    reason: Optional[str] = Field(
        default=None,
        title="Reason",
        description="status,optional users administrator comment related to the status. ",
        example="Email is not accepted....",
    )
    password: Optional[str] = Field(
        default=None,
        title="Password",
        description="Existing user can modify own email and must confirm it with token and password when email confirmation is on. ",
    )
