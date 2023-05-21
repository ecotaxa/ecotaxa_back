# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#
from API_models.filters import ProjectFiltersDict
from BO.ObjectSet import DescribedObjectSet
from DB.Sample import Sample
from DB.helpers import Session


class CommonObjectSets(object):
    """
    Some object sets which are used in several places.
    """

    @staticmethod
    def validatedInSample(session: Session, sample: Sample) -> DescribedObjectSet:
        obj_filter = ProjectFiltersDict(statusfilter="V", samples=str(sample.sampleid))
        obj_set: DescribedObjectSet = DescribedObjectSet(
            session, sample.projid, None, obj_filter
        )
        return obj_set

    @staticmethod
    def predictedInSample(session: Session, sample: Sample) -> DescribedObjectSet:
        obj_filter = ProjectFiltersDict(statusfilter="P", samples=str(sample.sampleid))
        obj_set: DescribedObjectSet = DescribedObjectSet(
            session, sample.projid, None, obj_filter
        )
        return obj_set
