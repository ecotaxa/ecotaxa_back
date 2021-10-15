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
        Something inside a directory, i.e. a sub-directory or a file.
    """
    name: str = Field(title="Name", description="atomic entry name.", example="task_281167_export_reduced_20200120_15_05.zip")
    type: str = Field(title="Type", description="entry type, 'D' for directory, 'F' for file.", example="F")
    size: int = Field(title="Size", description="Entry size, for zips.", example=173804090)
    mtime: str = Field(title="Modification time", description="Modification time, in ISO format.", example="2020-01-20 15:10:54.834571")


class DirectoryModel(BaseModel):
    """
        A path + list of entries inside. The path is relative to an implied root.
    """
    path: str = Field(title="Path", description="A /-separated path from root to this directory.", example="/ftp_plankton/Ecotaxa_Exported_data")
    entries: List[DirectoryEntryModel] = Field(title="Entries", description="Entries, i.e. subdirectories or contained files."
                                                     "All entries are readable, i.e. can be used as input or navigated into.")
