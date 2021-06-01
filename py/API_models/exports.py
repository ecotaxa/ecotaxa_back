# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum
from typing import List

from helpers.pydantic import BaseModel, Field


class EMODnetExportReq(BaseModel):
    """
        EMODNet format export request.
    """
    # meta: EMLMeta = Field(title="EML meta for the produced archive")
    project_ids: List[int] = Field(title="The projects to export", min_items=1)


class EMODnetExportRsp(BaseModel):
    """
        EMODNet format export response.
    """
    errors: List[str] = Field(title="Showstopper problems found while building the archive.",
                              default=[])
    warnings: List[str] = Field(title="Problems found while building the archive, which do not prevent producing it.",
                                default=[])
    job_id: int = Field(title="The created job, 0 if there were problems.",
                        default=0)


class ExportTypeEnum(str, Enum):
    general_tsv = 'TSV'
    backup = 'BAK'
    dig_obj_ident = 'DOI'
    summary = 'SUM'


class ExportReq(BaseModel):
    """
        Export request.
    """
    project_id: int = Field(title="The project to export")
    exp_type: ExportTypeEnum = Field(title="The export type: 'TSV', 'BAK', 'DOI' or 'SUM'.")
    tsv_entities: str = Field(title="For 'TSV' type, the entities to export, one letter for each of "
                                    "O(bject), P(rocess), A(cquisition), S(ample), "
                                    "classification H(istory), C(omments).")
    split_by: str = Field(title="For 'TSV' type, inside archives, split in one directory per... "
                                "'sample', 'taxo' or '' (no split)")
    coma_as_separator: bool = Field(title="For 'TSV' type, use a , instead of . for decimal separator.")
    format_dates_times: bool = Field(title="For 'TSV' type, format dates and times using - and : respectively.")
    with_images: bool = Field(title="For 'BAK' and 'DOI' types, export images as well.")
    with_internal_ids: bool = Field(title="For 'BAK' and 'DOI' types, export internal DB IDs.")
    only_first_image: bool = Field(title="For 'DOI' type, export only first (displayed) image.")
    sum_subtotal: str = Field(title="For 'SUM' type, how subtotals should be calculated. "
                                    "Per A(cquisition) or S(ample) or ''")
    out_to_ftp: bool = Field(title="Copy result file to FTP area. Original file is still available.")


class ExportRsp(EMODnetExportRsp):
    """
        Export response.
        TODO: Should inherit the other way round.
    """
