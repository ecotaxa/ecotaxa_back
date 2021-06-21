# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# An Object as seen by the user, i.e. the fields regardless of their storage.
# An Object cannot exist outside of a project due to "free" columns.
#
from typing import Tuple, List, Optional, Any

from sqlalchemy import MetaData

from BO.Acquisition import AcquisitionIDT
from BO.Classification import HistoricalClassificationListT, HistoricalClassification
from BO.Mappings import TableMapping
from BO.Sample import SampleIDT
from BO.helpers.MappedEntity import MappedEntity
from DB import ObjectHeader, ObjectFields, Image, ObjectsClassifHisto, User, Taxonomy
from DB.Project import ProjectIDT
from DB.helpers.ORM import Session, Query, joinedload, subqueryload, Model, minimal_model_of
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
    PROJECT_ACCESSOR = lambda obj: obj.acquisition.sample.project
    MAPPING_IN_PROJECT = 'object_mappings'

    def __init__(self, session: Session, object_id: ObjectIDT,
                 db_object: Optional[ObjectHeader] = None, db_fields: Optional[Model] = None):
        super().__init__(session)
        # Below is needed because validity test reads the attribute
        self.fields: Optional[ObjectFields] = None
        self.header: ObjectHeader
        if db_object is None:
            # Initialize from the unique ID
            qry: Query = self._session.query(ObjectHeader)
            qry = qry.filter(ObjectHeader.objid == object_id)
            qry = qry.options(joinedload(ObjectHeader.fields))
            qry = qry.options(subqueryload(ObjectHeader.all_images))
            self.header = qry.scalar()
            if self.header is None:
                return
            self.fields = self.header.fields
        else:
            # Initialize from provided models
            self.header = db_object
            self.fields = db_fields  # type:ignore
        self.sample_id = self.header.acquisition.acq_sample_id
        self.project_id = self.header.acquisition.sample.projid
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


class ObjectBOSet(object):
    """
        Lots of ObjectBOs, because working one by one is slow...
        Also cook a view on the fields in use
        TODO: Apply calculations onto set.
    """

    def __init__(self, session: Session, object_ids: Any, obj_mapping: TableMapping):
        needed_cols = obj_mapping.real_cols_to_tsv.keys()
        # noinspection PyPep8Naming
        ReducedObjectFields = minimal_model_of(MetaData(), ObjectFields, set(needed_cols))
        qry: Query = session.query(ObjectHeader, ReducedObjectFields)
        qry = qry.filter(ObjectHeader.objid.in_(object_ids))
        # noinspection PyUnresolvedReferences
        qry = qry.join(ReducedObjectFields, ObjectHeader.objid == ReducedObjectFields.objfid)  # type:ignore
        qry = qry.options(joinedload(ObjectHeader.all_images))
        self.all = [ObjectBO(session, 0, an_obj, its_fields) for an_obj, its_fields in qry.all()]
