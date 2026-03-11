# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum
from typing import List, Dict, Optional, Union

from pydantic import Extra, validator

from helpers.pydantic import BaseModel, Field


class ExportTypeEnum(str, Enum):
    """Externally deprecated"""

    general_tsv = "TSV"
    backup = "BAK"
    dig_obj_ident = "DOI"
    summary = "SUM"  # Historical summary
    abundances = (
        "ABO"  # Abundance summary https://github.com/ecotaxa/ecotaxa/issues/615
    )
    concentrations = (
        "CNC"  # Concentration summary https://github.com/ecotaxa/ecotaxa/issues/616
    )
    biovols = "BIV"  # Biovolume summary https://github.com/ecotaxa/ecotaxa/issues/617


class ExportFileTypeEnum(str, Enum):
    general_tsv = "general"
    backup = "backup"
    classification = "classification"
    summary = "summary"


class ExportSplitOptionsEnum(str, Enum):
    sample = "sample"
    acquisition = "acquisition"
    taxon = "taxon"
    none = "none"


class ExportImagesOptionsEnum(str, Enum):
    all = "all"
    first = "first"
    none = "none"


class SummaryExportQuantitiesOptionsEnum(str, Enum):
    abundance = (
        "abundance"  # Abundance summary https://github.com/ecotaxa/ecotaxa/issues/615
    )
    concentration = "concentration"  # Concentration summary https://github.com/ecotaxa/ecotaxa/issues/616
    biovolume = (
        "biovolume"  # Biovolume summary https://github.com/ecotaxa/ecotaxa/issues/617
    )


class SummaryExportSumOptionsEnum(str, Enum):
    none = "none"
    sample = "sample"
    acquisition = "acquisition"


class SciExportTypeEnum(str, Enum):
    """Computed export quantities"""

    # TODO: Identical to just above due to openapi.json generation. Find a workaround.
    abundances = "ABO"
    concentrations = "CNC"
    biovols = "BIV"


class SummaryExportGroupingEnum(str, Enum):
    """It's implied that we minimally group/aggregate by category AKA classification AKA taxon"""

    just_by_taxon = ""  # No other aggregation level
    by_sample = "S"
    by_subsample = "A"  # TODO: Temporary see below
    by_project = "P"  # Reserve for collections


class ProjectIdReq(BaseModel):
    """
    project_id or project_ids to export in a same zip with separated folders and tsv.
    """

    collection_id: Optional[int] = Field(
        title="Collection Id",
        description="The Collection to export if requested.",
        default=None,
        example=1,
    )
    project_id: Union[int, str] = Field(
        title="Project Id",
        description="The project(int) or projects (str, project ids list) to export.",
        example=1,
    )


class ExportReq(ProjectIdReq):
    """
    Export request.
    """

    exp_type: ExportTypeEnum = Field(
        title="Export type",
        description="The export type.",
        example=ExportTypeEnum.general_tsv,
    )
    use_latin1: bool = Field(
        title="Use latin1",
        description="Export using latin 1 character set, AKA iso-8859-1. Default is utf-8.",
        example=False,
        default=False,
    )
    tsv_entities: str = Field(
        title="Tsv entities",
        description="For 'TSV' type, the entities to export, one letter for each of "
        "O(bject), P(rocess), A(cquisition), S(ample), "
        "C(omments).",
        example="OPAS",
        default="",
    )
    only_annotations: bool = Field(
        title="Backup annotations",
        description="For 'BAK' type, only save objects' last annotation data in backup.",
        default=False,
        example=False,
    )
    split_by: str = Field(
        title="Split by",
        description="For 'TSV' type, inside archives, split in one directory per... "
        "'sample', 'acquisition', 'taxon' or '' (no split).",
        example="sample",
        default="",
    )
    coma_as_separator: bool = Field(
        title="Coma as separator",
        description="For 'TSV' type, use a , instead of . for decimal separator.",
        example=False,
        default=False,
    )
    format_dates_times: bool = Field(
        title="Format dates times",
        description="For 'TSV' type, format dates and times using - and : respectively.",
        example=False,
        default=True,
    )
    with_images: bool = Field(
        title="With images",
        description="For 'BAK' and 'DOI' types, export images as well.",
        example=False,
        default=False,
    )
    with_internal_ids: bool = Field(
        title="With internal ids",
        description="For 'TSV' type, export internal DB IDs.",
        example=False,
        default=False,
    )
    with_types_row: Optional[bool] = Field(
        title="With types row",
        description="Add an EcoTaxa-compatible second line with types.",
        example=False,
        default=False,
    )
    only_first_image: bool = Field(
        title="Only first image",
        description="For 'DOI' type, export only first (displayed) image.",
        example=False,
        default=False,
    )
    # TODO: Move A(acquisition) to U(subsample) but it needs propagation to client side.
    sum_subtotal: SummaryExportGroupingEnum = Field(
        title="Sum subtotal",
        description="For 'SUM', 'ABO', 'CNC' and 'BIV' types, if "
        "computations should be combined. "
        "Per A(cquisition) or S(ample) or <Empty>(just taxa).",
        example="A",
        default=SummaryExportGroupingEnum.just_by_taxon,
    )
    pre_mapping: Dict[int, Optional[int]] = Field(
        title="Categories mapping",
        description="For 'ABO', 'CNC' and 'BIV' types types, mapping "
        "from present taxon (key) to output replacement one (value)."
        " Use a null replacement to _discard_ the present taxon.",
        example={456: 956, 2456: 213},
        default={},
    )
    formulae: Dict[str, str] = Field(
        title="Computation formulas",
        description="Transitory: For 'CNC' and 'BIV' type, how to get values from DB "
        "free columns. Python syntax, prefixes are 'sam', 'ssm' and 'obj'."
        "Variables used in computations are 'total_water_volume', 'subsample_coef' "
        "and 'individual_volume'",
        example={
            "subsample_coef": "1/ssm.sub_part",
            "total_water_volume": "sam.tot_vol/1000",
            "individual_volume": "4.0/3.0*math.pi*(math.sqrt(obj.area/math.pi)*ssm.pixel_size)**3",
        },
        default={},
    )
    out_to_ftp: bool = Field(
        title="Out to ftp",
        description="Copy result file to FTP area. Original file is still available.",
        example=False,
        default=False,
    )

    # noinspection PyMethodParameters
    @validator("pre_mapping")
    def username_alphanumeric(cls, v):
        assert set(v.keys()).isdisjoint(
            set(v.values())
        ), "inconsistent pre_mapping, can't do remap chains or loops"
        return v

    class Config:
        schema_extra = {"title": "Export request Model"}


class GeneralExportReq(ProjectIdReq):
    """
    General purpose export request, produce a zip in a job with many options.
    """

    split_by: ExportSplitOptionsEnum = Field(
        title="Split by",
        description="If not none, separate (in ZIP sub-directories) output per given field.",
        example=ExportSplitOptionsEnum.sample,
        default=ExportSplitOptionsEnum.none,
    )
    with_images: ExportImagesOptionsEnum = Field(
        title="With images",
        description="Add in ZIP first (i.e. visible) image, all images, or no image.⚠️ 'all' means maybe several lines per object in TSVs.",
        example=ExportImagesOptionsEnum.first,
        default=ExportImagesOptionsEnum.none,
    )
    with_internal_ids: bool = Field(
        title="With internal ids",
        description="Export internal database IDs.",
        example=False,
        default=False,
    )
    with_types_row: bool = Field(
        title="With types row",
        description="Add an EcoTaxa-compatible second line with types.",
        example=False,
        default=False,
    )
    only_annotations: bool = Field(
        title="Backup annotations",
        description="Only save objects' last annotation data.",
        default=False,
        example=False,
    )
    # taxo_mapping: Dict[int, Optional[int]] = Field(
    #     title="Categories mapping",
    #     description="Mapping from present taxon (key) to output replacement one (value)."
    #     " Use a null replacement to _discard_ the present taxon.",
    #     example={456: 956, 2456: 213, 734: None},
    #     default={},
    # )
    out_to_ftp: bool = Field(
        title="Out to ftp",
        description="Copy result file to FTP area. Original file is still available.",
        default=False,
        example=False,
    )

    # noinspection PyMethodParameters
    # @validator("taxo_mapping")
    # def ensure_sane_remap(cls, v):
    #     assert set(v.keys()).isdisjoint(
    #         set(v.values())
    #     ), "inconsistent taxo_mapping, can't do remap chains or loops"
    #     return v

    class Config:
        schema_extra = {"title": "General Export request Model"}


class SummaryExportReq(ProjectIdReq):
    """
    Summary export request.
    """

    quantity: SummaryExportQuantitiesOptionsEnum = Field(
        title="Quantity",
        description="The quantity to compute. Abundance is always possible.",
        example=SummaryExportQuantitiesOptionsEnum.abundance,
        default=SummaryExportQuantitiesOptionsEnum.abundance,
    )
    summarise_by: SummaryExportSumOptionsEnum = Field(
        title="Summarise by",
        description="Computations aggregation level.",
        example=SummaryExportSumOptionsEnum.acquisition,
        default=SummaryExportSumOptionsEnum.sample,
    )
    taxo_mapping: Dict[int, Optional[int]] = Field(
        title="Categories mapping",
        description="Mapping "
        "from present taxon (key) to output replacement one (value)."
        " Use a 0 replacement to _discard_ the present taxon.",
        example={456: 956, 2456: 213, 7153: 0},
        default={},
    )
    formulae: Dict[str, str] = Field(
        title="Computation formulas",
        description="Transitory: How to get values from DB "
        "free columns. Python syntax, prefixes are 'sam', 'ssm' and 'obj'."
        "Variables used in computations are 'total_water_volume', 'subsample_coef' "
        "and 'individual_volume'",
        example={
            "subsample_coef": "1/ssm.sub_part",
            "total_water_volume": "sam.tot_vol/1000",
            "individual_volume": "4.0/3.0*math.pi*(math.sqrt(obj.area/math.pi)*ssm.pixel_size)**3",
        },
        default={},
    )
    out_to_ftp: bool = Field(
        title="Out to ftp",
        description="Copy result file to FTP area. Original file is still available.",
        default=False,
        example=False,
    )

    # noinspection PyMethodParameters
    @validator("taxo_mapping")
    def ensure_sane_remap(cls, v):
        assert set(v.keys()).isdisjoint(
            set(v.values())
        ), "inconsistent pre_mapping, can't do remap chains or loops"
        return v

    class Config:
        schema_extra = {"title": "Summary Export request Model"}


class BackupExportReq(ProjectIdReq):
    """
    Backup export request.
    """

    out_to_ftp: bool = Field(
        title="Out to ftp",
        description="Copy result file to FTP area. Original file is still available.",
        default=False,
        example=False,
    )

    class Config:
        schema_extra = {"title": "Backup Export request Model"}


class DarwinCoreExportReq(BaseModel):
    """
    Darwin Core format export request, only allowed format for a Collection. @see https://dwc.tdwg.org/
    """

    # Input
    collection_id: int = Field(
        title="Collection Id",
        description="The collection to export, by its internal Id.",
        example=1,
    )
    # Transform
    dry_run: bool = Field(
        title="Dry run",
        description="If set, then only a diagnostic of doability will be done.",
        example=False,
        default=False,
    )

    include_predicted: bool = Field(
        title="Include predicted",
        description="If set, then predicted objects, as well as validated ones, will be exported. "
        "A validation status will allow to distinguish between the two possible statuses.",
        example=False,
        default=False,
    )
    # Output
    with_absent: bool = Field(
        title="With absent",
        description="If set, then *absent* records will be generated, in the relevant samples, "
        "for categories present in other samples.",
        example=False,
        default=False,
    )
    with_computations: List[SciExportTypeEnum] = Field(
        title="With computations",
        description="Compute organisms abundances (ABO), concentrations (CNC) or biovolumes (BIV). Several possible.",
        example=["ABO"],
        default=[],
    )
    # TODO: Is same as TaxonomyRecast below, should get type TaxoRemappingT (or define it here)
    computations_pre_mapping: Dict[int, int] = Field(
        title="Computation mapping",
        description="Mapping from present taxon (key) to output replacement one (value), during computations."
        " Use a 0 replacement to _discard_ the objects with present taxon."
        " Note: These are EcoTaxa categories, WoRMS mapping happens after, whatever.",
        example={456: 956, 2456: 213, 93672: 0},
        default={},
    )
    formulae: Dict[str, str] = Field(
        title="Computation formulas",
        description="Transitory: How to get values from DB free columns. "
        "Python syntax, prefixes are 'sam', 'ssm' and 'obj'. "
        "Variables used in computations are 'total_water_volume', 'subsample_coef' and 'individual_volume'",
        example={
            "subsample_coef": "1/ssm.sub_part",
            "total_water_volume": "sam.tot_vol/1000",
            "individual_volume": "4.0/3.0*math.pi*(math.sqrt(obj.area/math.pi)*ssm.pixel_size)**3",
        },
        default={},
    )
    extra_xml: List[str] = Field(
        title="Extra XML",
        description="XML blocks which will be output, reformatted, inside the <dataset> tag of produced EML. "
        "Formal schema is in dataset section of: https://eml.ecoinformatics.org/schema/eml_xsd ",
        example={
            """<associatedParty>
    <individualName><givenName>Coco</givenName><surName>Rico</surName>
    </individualName>
    <organizationName>CHICK</organizationName>
      </associatedParty>""",
        },
        default=[],
    )

    # noinspection PyMethodParameters
    @validator("computations_pre_mapping")
    def ensure_consistent_mapping(cls, v):
        vals_but_0 = set(v.values()).difference({0})
        assert set(v.keys()).isdisjoint(
            vals_but_0
        ), "inconsistent pre_mapping, can't do remap chains or loops: common part is %s" % set(
            v.keys()
        ).intersection(
            set(v.values())
        )
        return v

    class Config:
        extra = Extra.forbid


class ExportRsp(BaseModel):
    """
    Export response, for all export jobs, either on Project or Collection.
    """

    errors: List[str] = Field(
        title="Errors",
        description="Showstopper problems found preventing building the archive.",
        example=[
            "No content produced.",
            " See previous warnings or check the presence of samples in the projects",
        ],
        default=[],
    )
    warnings: List[str] = Field(
        title="Warnings",
        description="Problems found while building the archive, which do not prevent producing it.",
        example=["No occurrence added for sample '3456' in 1"],
        default=[],
    )
    job_id: int = Field(
        title="Job Id",
        description="The created job, 0 if there were problems.",
        example=12376,
        default=0,
    )



