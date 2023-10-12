# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from formats.DarwinCore.models import DwC_Occurrence
from formats.TxtFromModels import TxtFileWithModel


class Occurrences(TxtFileWithModel):
    """
    The DwC Occurrences to export.
    """

    def __init__(self) -> None:
        super().__init__(DwC_Occurrence, "occurrence.txt")

    def add(self, an_occurrence: DwC_Occurrence) -> None:
        self.add_entity(an_occurrence)
