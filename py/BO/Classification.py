# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
from dataclasses import dataclass
from typing import Set, List, Iterable

# Typings, to be clear that these are not e.g. object IDs
ClassifIDT = int
ClassifIDListT = List[int]
ClassifScoresListT = List[float]
ClassifIDSetT = Set[int]
ClassifIDCollT = Iterable[int]


@dataclass()
class HistoricalLastClassif:
    """
    Association b/w an object and a former taxonomy entry.
    """

    objid: int
    classif_id: ClassifIDT
    histo_classif_date: datetime.datetime
    histo_classif_id: ClassifIDT
    histo_classif_qual: str
    histo_classif_who: int
    histo_training_id: int  # TODO: Mask in output?


HistoricalClassificationListT = List["HistoricalClassification"]


@dataclass()
class HistoricalClassification:
    """
    Former Taxonomy change operations onto an object, with names for display.
    """

    objid: int
    classif_id: ClassifIDT
    classif_date: datetime.datetime
    classif_who: int  # 'UserIDT' makes a circular dependency issue
    classif_qual: str
    classif_score: float
    user_name: str
    taxon_name: str
