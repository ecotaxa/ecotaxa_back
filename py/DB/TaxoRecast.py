# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#

from __future__ import annotations

from sqlalchemy import Identity

from DB.helpers.ORM import Model
from .helpers.DDL import Column, ForeignKey
from .helpers.Postgres import VARCHAR, INTEGER, JSONB

# Taxa are recast during Project prediction input phase, from reference dataset
# TODO: Migrate from project settings
PREDICTION_INPUT = "pre_predict"
# Taxa are recast during Project prediction output phase (unused)
PREDICTION_OUTPUT = "post_predict"
# Taxa are recast during Collection DWCA export
DWCA_EXPORT_OPERATION = "dwca_export"
# Taxa are recast during Project summary export
SUMM_EXPORT_OPERATION = "summary_export"
# Taxa recast during WoRMs move (unused)
TO_WORMS_OPERATION = "worms_migration"


class TaxoRecast(Model):
    """
    Make taxa appear as others (map) or disappear (filter) to an operation, in a given context.
    """

    __tablename__ = "taxo_recast"
    recast_id = Column(INTEGER, Identity(always=True), primary_key=True)
    # The context is: all projects in this specific collection
    collection_id: int = Column(
        INTEGER, ForeignKey("collection.id", ondelete="CASCADE"), nullable=True
    )
    # The context is: this specific project
    project_id: int = Column(
        INTEGER, ForeignKey("projects.projid", ondelete="CASCADE"), nullable=True
    )
    # During this operation
    operation: str = Column(VARCHAR(16), nullable=False)
    # Transforms in the form of a JSON object {from:to}, both taxa IDs, but from is a str
    # with 'to being null' means "filter out". Do some JSONB in case we need to query there.
    transforms = Column(JSONB, nullable=False)
    # Some doc per transform, JSON object with {from:doc}, from being str(ID) and doc being string
    documentation = Column(JSONB, nullable=False)

    def __str__(self):
        return "{0}/{1}/{2}".format(self.collection_id, self.project_id, self.operation)
