# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# An Object as seen by the user, i.e. the fields regardless of their storage.
# An Object cannot exist outside of a project due to "free" columns.
#
from typing import Tuple, List, Optional

from BO.Acquisition import AcquisitionIDT
from BO.Classification import HistoricalClassificationListT, HistoricalClassification
from BO.Project import ProjectIDT
from BO.Sample import SampleIDT
from BO.helpers.MappedEntity import MappedEntity
from DB import ObjectHeader, ObjectFields, Image, ObjectsClassifHisto, User, Taxonomy
from DB.helpers.ORM import Session, Query
from helpers.DynamicLogs import get_logger

# Typings, to be clear that these are not e.g. project IDs
ObjectIDT = int
ObjectIDWithParentsT = Tuple[ObjectIDT, AcquisitionIDT, SampleIDT, ProjectIDT]

logger = get_logger(__name__)


class ObjectBO(MappedEntity):
    """
        An object, as seen from user. No storage/DB-related distinction here.
    """
    FREE_COLUMNS_ATTRIBUTE = 'fields'

    def __init__(self, session: Session, object_id: ObjectIDT):
        super().__init__(session)
        # Main object
        self.header: ObjectHeader = self._session.query(ObjectHeader).get(object_id)
        self.fields: Optional[ObjectFields] = None
        if self.header is None:
            return
        # noinspection PyTypeChecker
        self.fields = self.header.fields
        # noinspection PyTypeChecker
        self.images: List[Image] = [an_img for an_img in self.header.all_images]

    def get_history(self) -> HistoricalClassificationListT:
        """
            Return classification history, user-displayable with names lookup but keeping IDs.
        """
        och = ObjectsClassifHisto
        qry: Query = self._session.query(och.objid, och.classif_id,
                                         och.classif_date, och.classif_who,
                                         och.classif_type, och.classif_qual,
                                         och.classif_score,
                                         User.name,
                                         Taxonomy.display_name).filter(
            ObjectsClassifHisto.objid == self.header.objid)
        qry = qry.outerjoin(User)
        qry = qry.outerjoin(Taxonomy, Taxonomy.id == och.classif_id)
        ret = [HistoricalClassification(rec) for rec in qry.all()]
        return ret

    def __getattr__(self, item):
        """ Fallback for 'not found' field after the C getattr() call.
            If we did not enrich/modify a Object field somehow then return it """
        try:
            return getattr(self.header, item)
        except AttributeError:
            return getattr(self.fields, item)
