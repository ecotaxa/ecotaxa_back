# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#

from __future__ import annotations
from enum import Enum
from sqlalchemy import Identity

from DB.helpers.ORM import Model
from .helpers.DDL import Column, ForeignKey
from .helpers.Postgres import VARCHAR, INTEGER, JSONB


class RecastOperation(str, Enum):
    # Taxa are recast during Project prediction input phase, from reference dataset
    prediction_input = "pre_predict"
    # Taxa are recast during Project prediction output phase (unused)
    prediction_output = "post_predict"
    # Taxa are recast to be used in Collection DWCA export
    dwca_export = "dwca_export"
    # Taxa are recast during Project summary export
    summary_export = "summary_export"
    # Taxa recast overwrite automatic worms recast
    overwrite_auto = "overwrite_auto"
    # Taxa recast in settings
    settings = "settings"


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
