# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Exported constants, to avoid data duplication b/w back-end and front-end
#
from typing import Dict, List, Optional

from BO.DataLicense import DataLicense, AccessLevelEnum
from DB.TaxoRecast import RecastOperation
from DB.User import UserStatus, UserType, PeopleOrganizationDirectory
from BO.User import (
    USER_PWD_REGEXP,
    USER_PWD_REGEXP_DESCRIPTION,
    SHORT_TOKEN_AGE,
    PROFILE_TOKEN_AGE,
)
from helpers.pydantic import BaseModel, Field

FORMULAE = """subsample_coef: 1/ssm.sub_part
total_water_volume: sam.tot_vol/1000
individual_volume: 4.0/3.0*math.pi*(math.sqrt(obj.area/math.pi)*ssm.pixel_size)**3"""


class Constants(BaseModel):
    """Values which can be considered identical over the lifetime of the back-end."""

    license_texts: Dict[str, str] = Field(
        title="License texts",
        description="The supported licenses and help text/links.",
        default={short: expl for short, expl in DataLicense.EXPLANATIONS.items()},
        example={
            "CC0 1.0": '<a href="https://creativecommons.org/publicdomain/zero/1.0/" rel="nofollow"><strong>CC-0</strong></a>: all registered EcoTaxa users are free to download, redistribute, modify, and build upon the data, with no conditions. Other databases can index the data. The data falls into the worldwide public domain. This is the license preferred by <a href="https://obis.org/manual/policy/" rel="nofollow">OBIS</a> and <a href="https://www.gbif.org/terms" rel="nofollow">GBIF</a>.',
            "CC BY 4.0": '<a href="https://creativecommons.org/licenses/by/4.0/" rel="nofollow"><strong>CC-BY</strong></a>: all registered EcoTaxa users are free to download, redistribute, modify, and build upon the data, as long as they cite the dataset and its authors. Other databases can index the data.',
            "CC BY-NC 4.0": '<a href="https://creativecommons.org/licenses/by-nc/4.0/" rel="nofollow"><strong>CC-BY-NC</strong></a>: all registered EcoTaxa users are free to download, redistribute, modify, and build upon the data, as long as they cite the dataset and its authors, and do not use it for commercial purpose ("primarily intended for or directed toward commercial advantage or monetary compensation"). Other databases can index the data.',
            "Copyright": "<strong>Copyright</strong>: only contributors to this project have rights on this data. This prevents its distribution in any kind of database.",
            "": "Not chosen",
        },
    )
    access: Dict[str, str] = Field(
        title="Project access",
        description="Project access levels.",
        default={st.name: st.value for st in AccessLevelEnum},
        example={"PUBLIC": "", "OPEN": "O", "PRIVATE": "P"},
    )

    app_manager: List[str] = Field(
        title="Application manager",
        description="The application manager identity (name, mail), from config file.",
        default=["", ""],
        min_items=2,
        max_items=2,
        example=["App manager Name", "app.manager@email.fr"],
    )
    countries: List[str] = Field(
        title="Countries",
        description="List of known countries names.",
        default=[],
        min_items=1,
        example=["France"],
    )
    people_organization_directories: Dict[str, str] = Field(
        title="People and organizations directories",
        description="Available directories to identify people and organizations in collections settings",
        default={st.name: st.value for st in PeopleOrganizationDirectory},
        example={"https://edmo.seadatanet.org/": "edmo", "https://orcid.org/": "orcid"},
    )
    user_status: Dict[str, int] = Field(
        title="User status",
        description="Application User status values",
        default={st.name: st.value for st in UserStatus},
        example={"blocked": -1, "inactive": 0, "active": 1, "pending": 2},
    )
    user_type: Dict[str, str] = Field(
        title="User status",
        description="Application User type values",
        default={st.name: st.value for st in UserType},
        example={"guest": "guest"},
    )
    password_regexp: str = Field(
        title="Password regexp",
        description=USER_PWD_REGEXP_DESCRIPTION,
        default=USER_PWD_REGEXP,
    )
    email_verification: bool = Field(
        title="Account email verification",
        description="Require verification before activation.",
        default=True,
    )
    account_validation: bool = Field(
        title="Account validation",
        description="Require validation by a Users Administrator before activation.",
        default=False,
    )
    short_token_age: int = Field(
        title="Short token lifespan",
        description="Email confirmation, password reset token lifespan.",
        default=SHORT_TOKEN_AGE,
    )
    profile_token_age: int = Field(
        title="Profile token lifespan",
        description="Profile modification token lifespan.",
        default=PROFILE_TOKEN_AGE,
    )
    recaptchaid: bool = Field(
        title="Google ReCaptcha",
        description="use Google ReCaptcha",
        default=False,
    )
    formulae: str = Field(
        title="Project Formulae",
        description="Project default concentration formulae",
        default=FORMULAE,
    )
    default_project_access: str = Field(
        title="access level",
        description="Project default access level",
        default=AccessLevelEnum.PUBLIC,
    )
    max_upload_size: int = Field(
        title="Max file size",
        description="My Files max file upload size (bytes)",
        default=681574400,
    )
    time_to_live: Optional[str] = Field(
        title="Time to live",
        description="My Files number of days before deleting directories",
        default=None,
    )
    all_in_one: bool = Field(
        title="All in One",
        description="local install - run without network access",
        default=False,
    )
    taxoserver_url: str = Field(
        title="EcoTaxoServer URL",
        description="url of taxonomy server ecotaxoserver",
        default="https://ecotaxoserver.obs-vlfr.fr/",
    )
    recast_operation: Dict[str, str] = Field(
        title="Recast operation",
        description="Taxonomy recast operation name",
        default={st.name: st.value for st in RecastOperation},
        example={"prediction_input": "pre_predict", "settings": "settings","dwca_export":"dwca_export"},
    )