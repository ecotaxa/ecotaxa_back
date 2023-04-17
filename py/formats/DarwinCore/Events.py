# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from formats.DarwinCore.models import DwC_Event
from formats.TxtFromModels import TxtFileWithModel


class Events(TxtFileWithModel):
    """
    The DwC Events we are going to export.
    """

    def __init__(self):
        super().__init__(DwC_Event, "event.txt")

    def add(self, an_event: DwC_Event):
        self.add_entity(an_event)
