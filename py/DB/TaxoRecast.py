# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2023  Picheral, Colin, Irisson (UPMC-CNRS)
#

from __future__ import annotations

from typing import List, TYPE_CHECKING

from DB.helpers.ORM import Model
from .helpers.DDL import Column, ForeignKey
from .helpers.Postgres import VARCHAR, INTEGER

PREDICTION_OPERATION = "predict"


class TaxoRecast(Model):
    """
        Make taxa appear as others (map) or disappear (filter) to an operation, in a given context.
    """
    __tablename__ = 'taxo_recast'
    # The context is: all projects in this specific collection
    collection_id: int = Column(INTEGER, ForeignKey('collection.id'), primary_key=True)
    # The context is: this specific project
    project_id: int = Column(INTEGER, ForeignKey('projects.projid'), primary_key=True)
    # During this operation
    operation: str = Column(VARCHAR(32), nullable=False, primary_key=True)
    # Transforms in the form of a dict/JSON object {from:to} with to being null means "filter out"
    transform = Column(VARCHAR, nullable=False)

    def __str__(self):
        return "{0}/{1}/{2}".format(self.collection_id, self.project_id, self.operation)
