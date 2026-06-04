# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)

from typing import Dict

from pydantic import BaseModel


class MigratedIDsRsp(BaseModel):
    projects: Dict[int, int]
    samples: Dict[int, int]
    acquisitions: Dict[int, int]
    objects: Dict[int, int]
