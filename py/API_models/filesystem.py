# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# FS entries description
#
from typing import List

from helpers.pydantic import BaseModel, Field


class DirectoryEntryModel(BaseModel):
    """
        Something inside a directory, i.e. a sub-directory or a file
    """
    name: str = Field(title="atomic entry name")
    type: str = Field(title="entry type, 'D' for directory, 'F' for file")
    size: int = Field(Title="Entry size, for zips")
    mtime: str = Field(Title="Modification time, in ISO format")


class DirectoryModel(BaseModel):
    """
        A path + list of entries inside. The path is relative to an implied root.
    """
    path: str = Field(title="A /-separated path from root to this directory")
    entries: List[DirectoryEntryModel] = Field(title="Entries, i.e. subdirectories or contained files. "
                                                     "All entries are readable, i.e. can be used as input or navigated into.")
