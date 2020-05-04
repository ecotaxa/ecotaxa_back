# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Dict, Union

from .pydantic import BaseModel, Field


class ImportPrepReq(BaseModel):
    """ Import preparation, request. """
    task_id: int = Field(title="The existing task to use")
    source_path: str = Field(title="Source path on server, to zip or plain dir")
    taxo_mappings: Dict[str, int] = Field(title="Optional taxonomy mapping", default={})
    skip_loaded_files: bool = Field(default=False)
    skip_existing_objects: bool = Field(default=False)


class ImportPrepRsp(BaseModel):
    """ Import preparation, response. """
    task_id: int = Field(title="The existing task used")
    source_path: str = Field(title="Eventually amended source path on server")
    taxo_mappings: Dict[str, int] = Field(title="Optional taxonomy mapping", default={})
    skip_loaded_files: bool
    skip_existing_objects: bool
    # OrderedDict is not available in typings of python 3.6
    # mappings: Dict[str, OrderedDict[str, str]] = Field(title="Fields mapping", default={})
    mappings: Dict[str, Dict[str, str]] = Field(title="Fields mapping", default={})
    found_users: Dict[str, Dict] = {}
    taxo_found: Dict[str, Union[int, None]] = {}
    not_found_users: List[str] = []
    not_found_taxo: List[str] = []
    warnings: List[str] = []
    errors: List[str] = []


class ImportRealReq(ImportPrepRsp):
    """ Import for real, request. """


class ImportRealRsp(BaseModel):
    """ Import for real, response. """
