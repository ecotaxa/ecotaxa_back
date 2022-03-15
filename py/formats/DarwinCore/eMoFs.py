# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from formats.DarwinCore.models import DwC_ExtendedMeasurementOrFact
from formats.TxtFromModels import TxtFileWithModel


class ExtendedMeasurementOrFacts(TxtFileWithModel):
    """
        AKA eMoF
    """

    def __init__(self):
        super().__init__(DwC_ExtendedMeasurementOrFact, "extendedmeasurementorfact.txt")

    def add(self, an_emof: DwC_ExtendedMeasurementOrFact):
        self.add_entity(an_emof)
