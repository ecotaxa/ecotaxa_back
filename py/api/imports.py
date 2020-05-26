# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Dict, Optional

from .pydantic import BaseModel, Field


class ImportPrepReq(BaseModel):
    """ Import preparation, request. """
    task_id: int = Field(title="The existing task to use")
    source_path: str = Field(title="Source path on server, to zip or plain directory")
    taxo_mappings: Dict[str, str] = Field(title="Optional taxonomy mapping", default={})
    skip_loaded_files: bool = Field(default=False)
    skip_existing_objects: bool = Field(default=False)
    update_mode: str = Field(title="Update data ('Yes'), including classification ('Cla')",
                             default="")


class ImportPrepRsp(BaseModel):
    """ Import preparation, response. """
    source_path: str = Field(title="Eventually amended source path on server")
    # OrderedDict is not available in typings of python 3.6
    # mappings: Dict[str, OrderedDict[str, str]] = Field(title="Fields mapping", default={})
    mappings: Dict[str, Dict[str, str]] = Field(title="Fields mapping", default={})
    found_users: Dict[str, Dict] = Field(title="Users found in TSV files",
                                         description="key = user name; value = "
                                                     "dict with (key = 'id' if resolved, else 'email')",
                                         default={})
    found_taxa: Dict[str, Optional[int]] = Field(title="Taxa found without ID in TSV files",
                                                 description="key = taxon NAME; value = "
                                                             "taxon ID if resolved, else None",
                                                 default={})
    warnings: List[str] = Field(title="Warnings from analysis", default=[])
    errors: List[str] = Field(title="Errors from analysis",
                              description="Do NOT proceed to real import if not empty.",
                              default=[])
    rowcount: int = Field(title="Number of TSV rows, counted during validation", default=0)


class ImportRealReq(BaseModel):
    """ Import for real, request. """
    task_id: int = Field(title="The existing task to use")
    source_path: str = Field(title="Source path on server, to plain directory")
    taxo_mappings: Dict[str, str] = Field(title="Optional taxonomy mapping", default={})
    skip_loaded_files: bool = Field(default=False)
    skip_existing_objects: bool = Field(default=False)
    update_mode: str = Field(title="Update data ('Yes'), including classification ('Cla')",
                             default="")
    # From step 1
    # TODO: Avoid duplication
    mappings: Dict[str, Dict[str, str]] = Field(title="Fields mapping", default={})
    found_users: Dict[str, Dict] = Field(title="Users found in TSV files",
                                         description="key = user name; value = "
                                                     "dict with (key = 'id' if resolved, else 'email')",
                                         default={})
    found_taxa: Dict[str, Optional[int]] = Field(title="Taxa found in TSV files",
                                                 description="key = taxon NAME; value = "
                                                             "taxon ID if resolved, else None",
                                                 default={})
    rowcount: int = Field(title="Number of TSV rows, counted during validation", default=0)


class ImportRealRsp(BaseModel):
    """ Import for real, response. """
