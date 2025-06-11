# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum
from typing import List, Dict

from helpers.pydantic import BaseModel, Field


class ImportReq(BaseModel):
    """Import request, from UI choices."""

    source_path: str = Field(
        title="Source path",
        description="Source path on server, to zip or plain directory."
        " \n \n The path can be returned by a file upload (absolute),"
        " \n \n otherwise it's relative to shared file area root.",
        example="/import_test.zip",
    )
    taxo_mappings: Dict[str, str] = Field(
        title="Taxo mappings",
        description="Optional taxonomy mapping, the key specifies the taxonomy ID found in file and the value specifies the final taxonomy ID to write.",
        default={},
        example={23444: 76543},
    )
    skip_loaded_files: bool = Field(
        default=False,
        title="Skip loaded files",
        description="If true skip loaded files, else don't.",
        example=False,
    )
    skip_existing_objects: bool = Field(
        default=False,
        title="Skip existing objects",
        description="If true skip existing objects, else don't.",
        example=False,
    )
    update_mode: str = Field(
        title="Update mode",
        description="Update data ('Yes'), including classification ('Cla').",
        default="",
        example="Yes",
    )

    class Config:
        schema_extra = {"title": "Import request Model"}


class ImportRsp(BaseModel):
    """Import response."""

    job_id: int = Field(
        title="Job Id", description="The job which was created for the run.", example=1
    )
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
    errors: List[str] = Field(
        title="Errors",
        description="Errors from analysis.",
        default=[],
        example=["new TSV file(s) are not compliant"],
    )
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
    datelb = "datelb"
    status = "status"


class SimpleImportReq(BaseModel):
    """Simple Import request."""

    source_path: str = Field(
        title="Source path",
        description="Source path on server, to zip or plain directory.",
        example="/import_test",
    )
    values: Dict[SimpleImportFields, str] = Field(
        title="Constant values, per field, to write for all images. If a field has no value don't include it.",
        description=":" + ", ".join(SimpleImportFields),
        example={
            SimpleImportFields.latitude: 43.69,
            SimpleImportFields.longitude: 7.30,
        },
    )
    # TODO: How to transmit a constant via OpenApi+FastApi ?
    # possible_values: List[str] = Field(title="Possible field values", const=True,
    #                                    default=[v for v in PossibleSimpleImportFields.__members__])
    possible_values: List[str] = [v for v in SimpleImportFields.__members__]

    class Config:
        schema_extra = {"title": "Simple import request Model"}


class SimpleImportRsp(BaseModel):
    """Simple Import, response."""

    job_id: int = Field(
        title="Job Id",
        description="The job which was created for the run. 0 if called with dry_run option.",
        example=1,
    )
    errors: List[str] = Field(
        title="Errors",
        description="Validation errors, dry_run or not.",
        example=[
            "'abcde' is not a valid value for SimpleImportFields.latitude",
            "'456.5' is not a valid value for SimpleImportFields.longitude",
            "'very very low' is not a valid value for SimpleImportFields.depthmin",
        ],
    )
