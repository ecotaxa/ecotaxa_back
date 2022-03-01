# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from .helpers.DDL import Index, Column, Sequence, ForeignKey
from .helpers.Direct import func
from .helpers.ORM import Model
from .helpers.Postgres import VARCHAR, INTEGER, CHAR, TIMESTAMP


class Taxonomy(Model):
    """
        A node in the taxonomy tree.
    """
    __tablename__ = 'taxonomy'
    # TODO: Remove the sequence. In fact, the unicity comes from EcoTaxoServer
    id: int = Column(INTEGER, Sequence('seq_taxonomy'), primary_key=True)
    parent_id = Column(INTEGER)
    name: str = Column(VARCHAR(100), nullable=False)
    id_source = Column(VARCHAR(20))
    taxotype: str = Column(CHAR(1), nullable=False, server_default='P')  # P = Phylo , M = Morpho
    # display_name is suffixed in EcoTaxoServer with (Deprecated) when taxostatus is 'D'
    display_name = Column(VARCHAR(200))  # Unique, to disambiguate ties in names
    lastupdate_datetime = Column(TIMESTAMP(precision=0))
    id_instance = Column(INTEGER)
    taxostatus: str = Column(CHAR(1), nullable=False,
                             server_default='A')  # N = Not approved, A = Approved, D = Deprecated
    # Was used to store temporarily a target id which current taxon should join
    # with all its assigned objects. Then the original category was deleted. So there is (as of 24/08/2021)
    # no DB line with this value set.
    # Is now used to store the _advised_ target taxon for a mass category change.
    rename_to = Column(INTEGER)
    source_url = Column(VARCHAR(200))
    source_desc = Column(VARCHAR(1000))
    creator_email = Column(VARCHAR(255))
    creation_datetime = Column(TIMESTAMP(precision=0))
    nbrobj = Column(INTEGER)  # Number of objects with this as classif_id
    nbrobjcum = Column(INTEGER)  # Number of objects with this, or any descendant, as classif_id

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


class TaxonomyChangeLog(Model):
    """
        Mass taxo/classification/category changes which happened before now, in a given project.
        Even if history, we don't keep track of deleted taxa/projects, hence the CASCADE.
    """
    __tablename__ = 'taxo_change_log'
    # _all_ objects with this category...
    from_id = Column(INTEGER, ForeignKey('taxonomy.id', ondelete="CASCADE"), nullable=False, primary_key=True)
    # ...moved to this category...
    to_id = Column(INTEGER, ForeignKey('taxonomy.id', ondelete="CASCADE"), nullable=False, primary_key=True)
    # ...in this project...
    project_id = Column(INTEGER, ForeignKey('projects.projid', ondelete="CASCADE"), nullable=False, primary_key=True)
    # ...for this reason.
    why = Column(VARCHAR(1), nullable=False)
    # It impacted this number of objects
    impacted = Column(INTEGER, nullable=False)
    # And occurred at this date
    occurred_on = Column(TIMESTAMP, nullable=False)

    def __str__(self):
        return "{0}->{1} on {2}".format(self.from_id, self.to_id, self.occurred_on)
