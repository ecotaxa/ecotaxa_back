# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum
from typing import List, Dict

from helpers.pydantic import BaseModel, Field


class ImportReq(BaseModel):
    """ Import request, from UI choices. """
    source_path: str = Field(title="Source path on server, to zip or plain directory")
    taxo_mappings: Dict[str, str] = Field(
        title="Optional taxonomy mapping, key=taxo ID found in file, value=final taxo ID to write", default={})
    skip_loaded_files: bool = Field(default=False)
    skip_existing_objects: bool = Field(default=False)
    update_mode: str = Field(title="Update data ('Yes'), including classification ('Cla')",
                             default="")


class ImportRsp(BaseModel):
    """ Import response. """
    job_id: int = Field(title="The job which was created for the run")
    # OrderedDict is not available in typings of python 3.6
    # mappings: Dict[str, OrderedDict[str, str]] = Field(title="Fields mapping", default={})
    # mappings: Dict[str, Dict[str, str]] = Field(title="Fields mapping", default={})
    # found_users: Dict[str, Dict] = Field(title="Users found in TSV files",
    #                                      description="key = user name; value = "
    #                                                  "dict with (key = 'id' if resolved, else 'email')",
    #                                      default={})
    # found_taxa: Dict[str, Optional[int]] = Field(title="Taxa found without ID in TSV files",
    #                                              description="key = taxon NAME; value = "
    #                                                          "taxon ID if resolved, else None",
    #                                              default={})
    # warnings: List[str] = Field(title="Warnings from analysis",
    #                             default=[])
    errors: List[str] = Field(title="Errors from analysis", default=[])
    # rowcount: int = Field(title="Number of TSV rows, just counted during validation, or loaded", default=0)


# class ImportRealReq(BaseModel):
#     """ Import for real, request. """
#     # From step 1
#     # TODO: Avoid duplication
#     mappings: Dict[str, Dict[str, str]] = Field(title="Fields mapping", default={})
#     found_users: Dict[str, Dict] = Field(title="Users found in TSV files",
#                                          description="key = user name; value = "
#                                                      "dict with (key = 'id' if resolved, else 'email')",
#                                          default={})
#     found_taxa: Dict[str, Optional[int]] = Field(title="Taxa found in TSV files",
#                                                  description="key = taxon NAME; value = "
#                                                              "taxon ID if resolved, else None",
#                                                  default={})
#     rowcount: int = Field(title="Number of TSV rows, counted during validation", default=0)
#
#
# class ImportRealRsp(BaseModel):
#     """ Import for real, response. """


class SimpleImportFields(str, Enum):
    imgdate = "imgdate"
    imgtime = "imgtime"
    latitude = "latitude"
    longitude = "longitude"
    depthmin = "depthmin"
    depthmax = "depthmax"
    taxolb = "taxolb"
    userlb = "userlb"
    status = "status"


class SimpleImportReq(BaseModel):
    """ Simple Import request. """
    source_path: str = Field(title="Source path on server, to zip or plain directory")
    values: Dict[SimpleImportFields, str] = Field(
        title="Constant values, per field, to write for all images. If a field has no value don't include it.",
        description=":" + ", ".join(SimpleImportFields))
    # TODO: How to transmit a constant via OpenApi+FastApi ?
    # possible_values: List[str] = Field(title="Possible field values", const=True,
    #                                    default=[v for v in PossibleSimpleImportFields.__members__])
    possible_values: List[str] = [v for v in SimpleImportFields.__members__]


class SimpleImportRsp(BaseModel):
    """ Simple Import, response. """
    job_id: int = Field(title="The job which was created for the run. 0 if called with dry_run option.")
    errors: List[str] = Field(title="Validation errors, dry_run or not.")
