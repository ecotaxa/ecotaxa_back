# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List

from formats.TxtFromModels import TxtFileWithModel


class DwcMetadata(object):
    """
        DwC metadata, describes the files inside DwC archive.
    """

    def __init__(self, dataset_meta_name: str):
        self.name = "meta.xml"
        self.dataset_meta_name = dataset_meta_name
        self.referred_to: List[TxtFileWithModel] = []

    def add(self, a_content):
        """
            It's assumed that the first list is the core.
        """
        self.referred_to.append(a_content)

    def content(self) -> str:
        xml = ['<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="%s">' % self.dataset_meta_name,
               self.referred_to[0].meta()]
        for more in range(1, len(self.referred_to)):
            # Only write extensions with data. Should not happen in production.
            if not self.referred_to[more].is_empty():
                xml.append(self.referred_to[more].meta())
        xml.append("</archive>\n")
        return "\n".join(xml)


DwC_Metadata = DwcMetadata
