# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Normalized vocabulary for various terms/quantities/computations.
#
from typing import Final


class Term(object):
    """
        A single term inside a vocabulary.
    """

    def __init__(self, concept: str, uri: str):
        self.concept = concept
        self.uri = uri


class Vocabulary(object):
    """
        What words mean exactly.
    """
    subsampling_coefficient: Final = Term("Sub-sampling coefficient",
                                          "http://vocab.nerc.ac.uk/collection/P01/current/SSAMPC01/1/")
    volume_sampled: Final = Term("Volume sampled of the water body",
                                 "http://vocab.nerc.ac.uk/collection/P01/current/VOLWBSMP/")
    biovolume: Final = Term("Biovolume of biological entity specified elsewhere per unit volume of the water body",
                            "http://vocab.nerc.ac.uk/collection/P01/current/CVOLUKNB/")


class Units(Vocabulary):
    """
        Set of well-defined measurement units.
    """
    dimensionless: Final = Term("Dimensionless", "http://vocab.nerc.ac.uk/collection/P06/current/UUUU/")
    cubic_metres: Final = Term("Cubic metres", "http://vocab.nerc.ac.uk/collection/P06/current/MCUB/")
    cubic_millimetres_per_cubic_metre: Final = Term("Cubic millimetres per cubic metre",
                                                    "http://vocab.nerc.ac.uk/collection/P06/current/CMCM/")
