# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)

from typing import Dict

from helpers.pydantic import BaseModel, Field


class MigratedIDsRsp(BaseModel):
    """
    Response for migrated IDs.
    """

    projects: Dict[int, int] = Field(
        title="Projects old->new",
        description="The mapping from old project IDs to new IDs.",
        example={1: 13, 3: 16},
    )
    samples: Dict[int, int] = Field(
        title="Samples old->new",
        description="The mapping from old sample IDs to new IDs.",
        example={10: 13000001, 11: 13000002},
    )
    acquisitions: Dict[int, int] = Field(
        title="Acquisitions/Processes old->new",
        description="The mapping from old acquisition/process IDs to new IDs.",
        example={20: 1300000001, 21: 1300000002},
    )
    objects: Dict[int, int] = Field(
        title="Objects old->new",
        description="The mapping from old object IDs to new IDs.",
        example={30: 13000000001, 31: 13000000002},
    )
