# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
from typing import Set, List, Iterable

from BO.helpers.DataclassAsDict import dataclass, DataclassAsDict

# Typings, to be clear that these are not e.g. object IDs
ClassifIDT = int
ClassifIDListT = List[int]
ClassifIDSetT = Set[int]
ClassifIDCollT = Iterable[int]


@dataclass(init=False)
class HistoricalClassif(DataclassAsDict):
    """
        Association b/w an object and a former taxonomy entry.
    """
    objid: int
    classif_id: ClassifIDT
    histo_classif_date: datetime.datetime
    histo_classif_type: str
    histo_classif_id: ClassifIDT
    histo_classif_qual: str
    histo_classif_who: int
