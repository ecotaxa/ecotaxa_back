# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from formats.DarwinCore.DatasetMeta import DatasetMetadata
from formats.DarwinCore.Events import Events
from formats.DarwinCore.Metadata import DwC_Metadata
from formats.DarwinCore.Occurences import Occurrences
from formats.DarwinCore.eMoFs import ExtendedMeasurementOrFacts


class DwcArchive(object):
    """
    A Darwin Core archive.
    """

    def __init__(self, meta: DatasetMetadata, path: Path):
        self.path = path
        """ The full path to the produced .zip """
        self.dataset_meta = meta
        self.meta = DwC_Metadata(self.dataset_meta.name)
        self.events = Events()
        self.meta.add(self.events)
        self.occurrences = Occurrences()
        self.meta.add(self.occurrences)
        self.emofs = ExtendedMeasurementOrFacts()
        self.meta.add(self.emofs)

    def build(self) -> None:
        """
        Build the produced archive file.
        """
        zipfile = ZipFile(
            self.path, mode="w", allowZip64=True, compression=ZIP_DEFLATED
        )
        parent_dir = self.path.parent
        # TODO: Better typings, classes below should have a trait
        all_files = [
            self.dataset_meta,
            self.meta,
            self.events,
            self.occurrences,
            self.emofs,
        ]
        for a_file in all_files:
            # Write the objects into real files
            dest_file = parent_dir / a_file.name  # type:ignore
            with open(dest_file, "w") as fd:
                fd.write(a_file.content())  # type:ignore
            # Add them to the zip
            zipfile.write(filename=dest_file, arcname=a_file.name)  # type:ignore


# camelCase is not good for concatenating acronyms
DwC_Archive = DwcArchive
