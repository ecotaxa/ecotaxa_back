# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict, Tuple, Union


class RanksPerObject(Dict[int, Union[int, Tuple[int, ...]]]):
    """
    Image ranks per object, kept in a compact form.
    Mem optimized: store an int for single-image case, and a tuple for several images.
    """

    def ranks_of(self, objid: int) -> Tuple[int, ...]:
        """
        Ranks of the given object, as a tuple, empty if the object is unknown.
        """
        present = self.get(objid)
        if present is None:
            return ()
        if type(present) is int:
            return (present,)
        return present

    def add(self, objid: int, rank: int) -> None:
        """
        Record an image rank for an object, staying compact as long as the object
        has a single image. Adding an already present rank is a no-op.
        """
        present = self.get(objid)
        if present is None:
            self[objid] = rank
        elif type(present) is int:
            if present != rank:
                self[objid] = (present, rank)
        elif rank not in present:
            self[objid] = present + (rank,)
