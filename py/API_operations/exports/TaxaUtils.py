# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from typing import Dict, Optional

from sqlalchemy.orm import Session

from API_operations.TaxoManager import TaxonomyChangeService
from DB import WoRMS
from DB.helpers.ORM import Query
from helpers.DynamicLogs import get_logger
from providers.WoRMS import WoRMSFinder

logger = get_logger(__name__)

ALL_RANKS = {
    "Kingdom": 1,
    "Subkingdom": 2,
    "Infrakingdom": 3,
    "Phylum": 4,
    "Class": 5,
    "Subclass": 6,
    "Order": 7,
    "Suborder": 8,
    "Family": 9,
    "Species": 10,
    "Subfamily": 11,
    "Genus": 12,
}
RANKS_BY_ID = {v: k for k, v in ALL_RANKS.items()}
