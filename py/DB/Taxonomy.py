# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from .helpers.DDL import Index, Column, Sequence, func
from .helpers.ORM import Model
from .helpers.Postgres import VARCHAR, INTEGER, CHAR, TIMESTAMP


class Taxonomy(Model):
    """
        A node in the taxonomy tree.
    """
    __tablename__ = 'taxonomy'
    id = Column(INTEGER, Sequence('seq_taxonomy'), primary_key=True)
    parent_id = Column(INTEGER)
    name = Column(VARCHAR(100), nullable=False)
    id_source = Column(VARCHAR(20))
    taxotype = Column(CHAR(1), nullable=False, server_default='P')  # P = Phylo , M = Morpho
    display_name = Column(VARCHAR(200))  # Unique, to disambiguate ties in names
    lastupdate_datetime = Column(TIMESTAMP(precision=0))
    id_instance = Column(INTEGER)
    taxostatus = Column(CHAR(1), nullable=False, server_default='A')
    rename_to = Column(INTEGER)
    source_url = Column(VARCHAR(200))
    source_desc = Column(VARCHAR(1000))
    creator_email = Column(VARCHAR(255))
    creation_datetime = Column(TIMESTAMP(precision=0))
    nbrobj = Column(INTEGER)
    nbrobjcum = Column(INTEGER)

    def __str__(self):
        return "{0} ({1})".format(self.name, self.id)


Index('IS_TaxonomyParent', Taxonomy.parent_id)
Index('IS_TaxonomySource', Taxonomy.id_source)
Index('IS_TaxonomyNameLow', func.lower(Taxonomy.name))
Index('IS_TaxonomyDispNameLow',
      func.lower(Taxonomy.display_name))  # create index IS_TaxonomyDispNameLow on taxonomy(lower(display_name));


class TaxonomyTreeInfo(Model):
    """
        Information about the whole taxonomy table/tree. So far a single line.
    """
    __tablename__ = 'persistantdatatable'  # The most pleonasmic DB table name _ever_
    id = Column(INTEGER, primary_key=True)
    lastserverversioncheck_datetime = Column(TIMESTAMP(precision=0))
