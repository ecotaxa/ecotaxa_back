# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum
from typing import List, Dict, Optional

from helpers.pydantic import BaseModel, Field


class DarwinCoreExportReq(BaseModel):
    """
        Darwin Core format export request. @see https://dwc.tdwg.org/
    """
    # meta: EMLMeta = Field(title="EML meta for the produced archive")
    project_ids: List[int] = Field(title="Project Ids", description="The projects to export.", min_items=1)


class DarwinCoreExportRsp(BaseModel):
    """
        Darwin Core format export response.
    """
    errors: List[str] = Field(title="Errors", description="Showstopper problems found preventing building the archive.",
                              example=["No content produced.",
                                       " See previous warnings or check the presence of samples in the projects"],
                              default=[])
    warnings: List[str] = Field(title="Warnings",
                                description="Problems found while building the archive, which do not prevent producing it.",
                                example=["No occurrence added for sample '3456' in 1"], default=[])
    job_id: int = Field(title="Job Id", description="The created job, 0 if there were problems.",
                        example=12376, default=0)


class ExportTypeEnum(str, Enum):
    general_tsv = 'TSV'
    backup = 'BAK'
    dig_obj_ident = 'DOI'
    summary = 'SUM'  # Historical summary
    abundances = 'ABO'  # Abundance summary https://github.com/ecotaxa/ecotaxa/issues/615
    concentrations = 'CNC'  # Concentration summary https://github.com/ecotaxa/ecotaxa/issues/616
    biovols = 'BIV'  # Biovolume summary https://github.com/ecotaxa/ecotaxa/issues/617


class SummaryExportGroupingEnum(str, Enum):
    """ It's implied that we also group by category AKA classification AKA taxon """
    just_by_taxon = ''  # Just group by the implied taxa
    by_project = 'P'  # Reserve for collections
    by_sample = 'S'
    by_subsample = 'A'  # TODO: Temporary see below


class ExportReq(BaseModel):
    """
        Export request.
    """
    project_id: int = Field(title="Project Id", description="The project to export.", example=1)
    exp_type: ExportTypeEnum = Field(title="Export type", description="The export type: 'TSV', 'BAK', 'DOI' or 'SUM'.",
                                     example=ExportTypeEnum.general_tsv)
    use_latin1: bool = Field(default=False,
                             title="Use latin1",
                             description="Export using latin 1 character set, AKA iso-8859-1. Default is utf-8.",
                             example=False)
    tsv_entities: str = Field(title="Tsv entities",
                              description="For 'TSV' type, the entities to export, one letter for each of "
                                          "O(bject), P(rocess), A(cquisition), S(ample), "
                                          "classification H(istory), C(omments).", example="OPAS")
    split_by: str = Field(title="Split by",
                          description="For 'TSV' type, inside archives, split in one directory per... "
                                      "'sample', 'taxo' or '' (no split).", example='sample')
    coma_as_separator: bool = Field(title="Coma as separator",
                                    description="For 'TSV' type, use a , instead of . for decimal separator.",
                                    example=False)
    format_dates_times: bool = Field(title="Format dates times",
                                     description="For 'TSV' type, format dates and times using - and : respectively.",
                                     example=False)
    with_images: bool = Field(title="With images", description="For 'BAK' and 'DOI' types, export images as well.",
                              example=False)
    with_internal_ids: bool = Field(title="With internal ids",
                                    description="For 'BAK' and 'DOI' types, export internal DB IDs.", example=False)
    only_first_image: bool = Field(title="Only first image",
                                   description="For 'DOI' type, export only first (displayed) image.", example=False)
    # TODO: Move A(acquisition) to U(subsample) but it needs propagation to client side.
    sum_subtotal: SummaryExportGroupingEnum = Field(title="Sum subtotal",
                                                    description="For 'SUM', 'ABO', 'CNC' and 'BIV' types, if "
                                                                "computations should be combined."
                                                                "Per A(cquisition) or S(ample) or <Empty>(just taxa).",
                                                    example="A")
    pre_mapping: Dict[int, Optional[int]] = Field(title="Categories mapping",
                                                  description="For 'ABO', 'CNC' and 'BIV' types types, mapping "
                                                              "from present taxon (key) to output replacement one (value)."
                                                              " Use a null replacement to dicard the present taxon.",
                                                  example={456: 956, 2456: 213}, default={})
    formulae: Dict[str, str] = Field(title="Computation formulas",
                                     description="Transitory: For 'CNC' and 'BIV' type, how to get values from DB "
                                                 "free columns. Python syntax, prefixes are 'sam', 'ssm' and 'obj'.",
                                     example={"SubSamplingCoefficient": "1/ssm.sub_part",
                                              "VolWBodySamp": "sam.tot_vol/1000",
                                              "IndividualBioVol": "4.0/3.0*math.pi*(math.sqrt(obj.area/math.pi)*ssm.pixel_size)**3"},
                                     default={}
                                     )
    out_to_ftp: bool = Field(title="Out to ftp",
                             description="Copy result file to FTP area. Original file is still available.",
                             example=False)

    class Config:
        schema_extra = {"title": "Export request Model"}


# TODO: Should inherit the other way round.
class ExportRsp(DarwinCoreExportRsp):
    """
        Export response.
    """
