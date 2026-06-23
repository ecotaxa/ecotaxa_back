# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Set, List, Iterable, Optional

# Typings, to be clear that these are not e.g. object IDs
ClassifIDT = int
ClassifIDListT = List[int]
ClassifScoresListT = List[float]
ClassifIDSetT = Set[int]
ClassifIDCollT = Iterable[int]


class HistoClassifType(str, Enum):
    MANUAL = "M"
    AUTO = "A"
    NOTHING = "n"


@dataclass()
class HistoricalLastClassif:
    """
    Association b/w an object and a former taxonomy entry, if any.
    This is _not_ the last historical line from DB table. If there is no history, it reflects
    current state of the object, including nothing if it was simply imported. Arguable.
    """

    objid: int
    classif_id: Optional[ClassifIDT]
    histo_classif_date: Optional[datetime.datetime]
    histo_classif_id: Optional[ClassifIDT]
    histo_classif_type: Optional[str]  # TODO:  HistoClassifType Enum
    histo_classif_qual: Optional[str]
    histo_classif_who: Optional[int]
    histo_classif_score: Optional[float]


HistoricalClassificationListT = List["HistoricalClassification"]


@dataclass()
class HistoricalClassification:
    """
    Former Taxonomy change operations onto an object, with names for display.
    """

    objid: int
    classif_id: ClassifIDT
    classif_date: datetime.datetime
    classif_who: Optional[int]  # TODO: 'UserIDT' makes a circular dependency issue
    classif_type: str
    classif_qual: str
    classif_score: Optional[float]
    user_name: Optional[str]
    taxon_name: str
