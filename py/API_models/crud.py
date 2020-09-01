# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Models used in CRUD API_operations.
#
from typing import Optional

from typing_extensions import TypedDict

from DB import User, Project
from helpers.pydantic import BaseModel, Field
from .helpers.DBtoModel import sqlalchemy_to_pydantic
from .helpers.TypedDictToModel import parse_typed_dict

UserModel = sqlalchemy_to_pydantic(User)
ProjectModel = sqlalchemy_to_pydantic(Project)


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
           other: direct comparison with DB value """
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
