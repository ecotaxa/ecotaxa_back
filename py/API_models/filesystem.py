# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# FS entries description
#
from typing import List, Optional

from helpers.pydantic import BaseModel, Field


class DirectoryEntryModel(BaseModel):
    """
    Something inside a directory, i.e. a sub-directory or a file.
    """

    name: str = Field(
        title="Name",
        description="atomic entry name.",
        examples=["task_281167_export_reduced_20200120_15_05.zip"],
    )
    type: str = Field(
        title="Type",
        description="entry type, 'D' for directory, 'F' for file.",
        examples=["F"],
    )
    size: int = Field(
        title="Size", description="Entry size, for zips.", examples=[173804090]
    )
    mtime: str = Field(
        title="Modification time",
        description="Modification time, in ISO format.",
        examples=["2020-01-20 15:10:54.834571"],
    )


class DirectoryModel(BaseModel):
    """
    A path + list of entries inside. The path is relative to an implied root.
    """

    path: str = Field(
        title="Path",
        description="A /-separated path from root to this directory.",
        examples=["/ftp_plankton/Ecotaxa_Exported_data"],
    )
    entries: List[DirectoryEntryModel] = Field(
        title="Entries",
        description="Entries, i.e. subdirectories or contained files."
        "All entries are readable, i.e. can be used as input or navigated into.",
    )


class UnpackStatusModel(BaseModel):
    """
    Status of the unpacking of an archive uploaded with TUS, to poll until state is 'done' or 'error'.
    """

    state: str = Field(
        title="State",
        description="'unpacking', then 'done' or 'error'.",
        examples=["unpacking"],
    )
    name: str = Field(
        title="Name", description="Uploaded file name.", examples=["b_da_19.zip"]
    )
    percent: int = Field(
        default=0,
        title="Percent",
        description="Progress, 0 to 100. Counts the entries of the uploaded archive checked or, "
        "for nested archives, unpacked. It does not move while the files of an archive are written, "
        "so for one big archive without nested ones it stays low, then jumps to 100.",
        examples=[42],
    )
    entries_done: Optional[int] = Field(
        default=None,
        title="Entries done",
        description="Entries of the uploaded archive done.",
        examples=[420],
    )
    entries_total: Optional[int] = Field(
        default=None,
        title="Entries total",
        description="Entries of the uploaded archive, once its headers are read.",
        examples=[1000],
    )
    files_done: Optional[int] = Field(
        default=None,
        title="Files done",
        description="Files unpacked so far, nested archives included.",
        examples=[12000],
    )
    bytes_done: Optional[int] = Field(
        default=None,
        title="Bytes done",
        description="Bytes unpacked so far, nested archives included.",
        examples=[123456789],
    )
    bytes_declared: Optional[int] = Field(
        default=None,
        title="Bytes declared",
        description="Uncompressed size declared by the uploaded archive, nested archives not included.",
        examples=[223456789],
    )
    result_paths: Optional[List[str]] = Field(
        default=None,
        title="Result paths",
        description="When done, where the result is in My Files.",
        examples=[["my_folder/b_da_19"]],
    )
    message: Optional[str] = Field(
        default=None,
        title="Message",
        description="When error, why nothing was kept.",
        examples=["[UnprocessableEntityException] Archive is corrupt: Bad CRC-32 for file 'a.tsv'"],
    )
    updated: str = Field(
        title="Updated",
        description="Last update, UTC ISO format.",
        examples=["2026-11-12T14:00:00.123456+00:00"],
    )
