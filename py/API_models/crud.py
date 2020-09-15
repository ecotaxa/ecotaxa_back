# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in CRUD API_operations.
#
from typing import Optional, Dict, Type, Iterable, List

from sqlalchemy.sql.functions import current_timestamp
from typing_extensions import TypedDict

from DB import User, Project, Sample, Acquisition, Process, ObjectHeader
from helpers.pydantic import BaseModel, Field
from .helpers.DBtoModel import sqlalchemy_to_pydantic
from .helpers.TypedDictToModel import parse_typed_dict

# Direct mirror of DB models
UserModel = sqlalchemy_to_pydantic(User)
SampleModel = sqlalchemy_to_pydantic(Sample)
AcquisitionModel = sqlalchemy_to_pydantic(Acquisition)
ProcessModel = sqlalchemy_to_pydantic(Process)
ObjectHeaderModel = sqlalchemy_to_pydantic(ObjectHeader)
# This one goes over the limit of 255 fields in OpenAPI generator
# ObjectFieldsModel = sqlalchemy_to_pydantic(ObjectFields)

# Enriched model
FreeColT = Dict[str, str]


class _AddedToProject(BaseModel):
    obj_free_cols: FreeColT = Field(title="Object free columns",
                                    default={})
    sample_free_cols: FreeColT = Field(title="Sample free columns",
                                       default={})
    acquisition_free_cols: FreeColT = Field(title="Acquisition free columns",
                                            default={})
    process_free_cols: FreeColT = Field(title="Process free columns",
                                        default={})

    class Config:
        schema_extra = {
            "example": {
                "obj_free_cols": {"area": "n01", "esd": "n02"},
                "sample_free_cols": {"barcode": "t01"},
                "acquisition_free_cols": {"flash_delay": "t01"},
                "process_free_cols": {"nb_images": "t01"},
            }
        }


# TODO: Example for project fields
_ProjectModelFromDB: Type = sqlalchemy_to_pydantic(Project)


# TODO: when python 3.7+, we can have pydantic generics and remove the ignore below
class ProjectModel(_ProjectModelFromDB, _AddedToProject):  # type:ignore
    """
        Project + computed
    """


class CreateProjectReq(BaseModel):
    clone_of_id: int = Field(title="If set, clone specified Project",
                             default=None)
    title: str = Field(title="The project title")
    visible: bool = Field(title="The project is created visible",
                          default=True)


class ProjectSearchResult(BaseModel):
    projid: int
    title: str
    status: str
    objcount: int
    pctvalidated: float
    pctclassified: float
    email: Optional[str]
    name: Optional[str]
    visible: bool


class ProjectFilters(TypedDict, total=False):
    taxo: Optional[str]
    """ Only include object classified in taxonomy/category with given numeric id """
    taxochild: Optional[str]
    """ If 'Y' and taxo is set, also include children in taxonomy tree """
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


ProjectFiltersModel = parse_typed_dict(ProjectFilters)


class ColUpdate(TypedDict):
    ucol: str
    """ A column name, pseudo-columns AKA free ones, are OK """
    uval: str
    """ The new value to set, always as a string """


class ColUpdateList(list):
    """
        Formalized way of updating entities in the system.
            It's on purpose not a Dict as we take provision for futures usage when we need an order.
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
