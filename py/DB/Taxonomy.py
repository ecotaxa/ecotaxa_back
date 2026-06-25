# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from datetime import datetime
from enum import Enum
from typing import List

from sqlalchemy.orm import mapped_column

from .helpers.DDL import Index, Sequence, ForeignKey
from .helpers.Direct import func
from .helpers.ORM import Model, Mapped
from .helpers.Postgres import VARCHAR, INTEGER, CHAR, TIMESTAMP

TaxonomyIDT = int
TaxonomyIDListT = List[int]


class ExtendedEnum(Enum):

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


class TaxoStatus(str, ExtendedEnum):
    approved = "A"
    notapproved = "N"
    deprecated = "D"


class TaxoType(str, ExtendedEnum):
    morpho = "M"
    phylo = "P"


class Taxonomy(Model):
    """
    A node in the taxonomy tree.
    """

    __tablename__ = "taxonomy"
    # TODO: Remove the sequence. In fact, the unicity comes from EcoTaxoServer
    id: Mapped[int] = mapped_column(INTEGER, Sequence("seq_taxonomy"), primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(INTEGER)
    aphia_id: Mapped[int | None] = mapped_column(INTEGER)
    rank: Mapped[str | None] = mapped_column(VARCHAR(24))
    name: Mapped[str] = mapped_column(VARCHAR(100))
    taxotype: Mapped[str] = mapped_column(
        CHAR(1), server_default="P"
    )  # P = Phylo , M = Morpho
    # display_name is suffixed in EcoTaxoServer with (Deprecated) when taxostatus is 'D'
    display_name: Mapped[str | None] = mapped_column(VARCHAR(200))  # Unique, to disambiguate ties in names
    lastupdate_datetime: Mapped[datetime | None] = mapped_column(TIMESTAMP(precision=0))
    id_instance: Mapped[int | None] = mapped_column(INTEGER)
    taxostatus: Mapped[str] = mapped_column(
        CHAR(1), server_default="A"
    )  # N = Not approved, A = Approved, D = Deprecated
    # Was used to store temporarily a target id which current taxon should join
    # with all its assigned objects. Then the original category was deleted. So there is (as of 24/08/2021)
    # no DB line with this value set.
    # Is now used to store the _advised_ target taxon for a mass category change.
    rename_to: Mapped[int | None] = mapped_column(INTEGER)
    source_url: Mapped[str | None] = mapped_column(VARCHAR(200))
    source_desc: Mapped[str | None] = mapped_column(VARCHAR(1000))
    creator_email: Mapped[str | None] = mapped_column(VARCHAR(255))
    creation_datetime: Mapped[datetime | None] = mapped_column(TIMESTAMP(precision=0))
    nbrobj: Mapped[int | None] = mapped_column(INTEGER)  # Number of objects with this as classif_id
    nbrobjcum: Mapped[int | None] = mapped_column(
        INTEGER
    )  # Number of objects with this, or any descendant, as classif_id

    def __str__(self):
        return "{0} ({1})".format(self.name, self.id)


Index("IS_TaxonomyParent", Taxonomy.parent_id)
Index("IS_TaxonomyAphiaId", Taxonomy.aphia_id)
Index("IS_TaxonomyNameLow", func.lower(Taxonomy.name))
Index(
    "IS_TaxonomyDispNameLow", func.lower(Taxonomy.display_name)
)  # create index IS_TaxonomyDispNameLow on taxonomy(lower(display_name));


class TaxonomyTreeInfo(Model):
    """
    Information about the whole taxonomy table/tree. So far a single line.
    """

    __tablename__ = "persistantdatatable"  # The most pleonasmic DB table name _ever_
    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    lastserverversioncheck_datetime: Mapped[datetime | None] = mapped_column(TIMESTAMP(precision=0))


class TaxonomyChangeLog(Model):
    """
    Mass taxo/classification/category changes which happened before now, in a given project.
    Even if history, we don't keep track of deleted taxa/projects, hence the CASCADE.
    """

    __tablename__ = "taxo_change_log"
    # _all_ objects with this category...
    from_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey("taxonomy.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # ...moved to this category...
    to_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey("taxonomy.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # ...in this project...
    project_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey("projects.projid", ondelete="CASCADE"),
        primary_key=True,
    )
    # ...for this reason.
    why: Mapped[str] = mapped_column(VARCHAR(1))
    # It impacted this number of objects
    impacted: Mapped[int] = mapped_column(INTEGER)
    # And occurred at this date
    occurred_on: Mapped[datetime] = mapped_column(TIMESTAMP)

    def __str__(self):
        return "{0}->{1} on {2}".format(self.from_id, self.to_id, self.occurred_on)
