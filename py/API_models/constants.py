# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Exported constants, to avoid data duplication b/w back-end and front-end
#
from typing import Dict, List, NamedTuple

from BO.DataLicense import DataLicense
from DB.User import UserStatus
from BO.User import (
    USER_PWD_REGEXP,
    USER_PWD_REGEXP_DESCRIPTION,
    SHORT_TOKEN_AGE,
    PROFILE_TOKEN_AGE,
)
from helpers.pydantic import BaseModel, Field


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
    user_status: Dict[str, int] = Field(
        title="User status",
        description="Application User status values",
        default={st.name: st.value for st in UserStatus},
        example={"blocked": -1, "inactive": 0, "active": 1, "pending": 2},
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
