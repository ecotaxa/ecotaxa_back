# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Dict, Tuple, TypeVar, Union

K = TypeVar("K", int, str)


class RanksPerObject(Dict[K, Union[int, Tuple[int, ...]]]):
    """
    Image ranks per object, kept in a compact form.
    Mem optimized: store an int for single-image case, and a tuple for several images.
    """

    def ranks_of(self, objid: K) -> Tuple[int, ...]:
        """
        Ranks of the given object, as a tuple, empty if the object is unknown.
        """
        present = self.get(objid)
        if present is None:
            return ()
        if isinstance(present, int):
            return (present,)
        return present

    def add(self, objid: K, rank: int) -> None:
        """
        Record an image rank for an object, staying compact as long as the object
        has a single image. Adding an already present rank is a no-op.
        """
        present = self.get(objid)
        if present is None:
            self[objid] = rank
        elif isinstance(present, int):
            if present != rank:
                self[objid] = (present, rank)
        elif rank not in present:
            self[objid] = present + (rank,)

    def merge(self, other: "RanksPerObject[K]") -> None:
        """
        Merge another RanksPerObject into this one.
        """
        for objid, ranks in other.items():
            if objid not in self:
                self[objid] = ranks
            elif isinstance(ranks, int):
                self.add(objid, ranks)
            else:
                for rank in ranks:
                    self.add(objid, rank)
