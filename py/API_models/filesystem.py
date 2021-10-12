# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# FS entries description
#
from typing import List

from helpers.pydantic import BaseModel, Field

#TODO JCE - examples
class DirectoryEntryModel(BaseModel):
    """
        Something inside a directory, i.e. a sub-directory or a file.
    """
    name: str = Field(title="Name", description="atomic entry name.", example="")
    type: str = Field(title="Type", description="entry type, 'D' for directory, 'F' for file.", example="")
    size: int = Field(title="Size", description="Entry size, for zips.", example=1)
    mtime: str = Field(title="Modification time", description="Modification time, in ISO format.", example="")


#TODO JCE - examples
class DirectoryModel(BaseModel):
    """
        A path + list of entries inside. The path is relative to an implied root.
    """
    path: str = Field(title="Path", description="A /-separated path from root to this directory.", example="")
    entries: List[DirectoryEntryModel] = Field(title="Entries", description="Entries, i.e. subdirectories or contained files."
                                                     "All entries are readable, i.e. can be used as input or navigated into.")
