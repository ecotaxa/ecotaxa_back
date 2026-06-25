# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Collection i.e. set of projects.
#

from typing import TYPE_CHECKING, List

from sqlalchemy.orm import mapped_column

from DB.helpers.ORM import Model, Mapped
from .helpers.DDL import Sequence, ForeignKey, Index
from .helpers.Postgres import VARCHAR, INTEGER

if TYPE_CHECKING:
    from .Project import Project
    from .User import User, Guest, Organization


class Collection(Model):
    """A set of projects see #82, #335, #519"""

    __tablename__ = "collection"
    id: Mapped[int] = mapped_column(INTEGER, Sequence("collection_id_seq"), primary_key=True)
    """ Internal identifier """
    external_id: Mapped[str] = mapped_column(VARCHAR)
    """ External identifier, e.g. doi:10.xxxx/eml.1.1 """
    external_id_system: Mapped[str] = mapped_column(VARCHAR)
    """ External identifier system, e.g. https://doi.org """
    provider_user_id: Mapped[int | None] = mapped_column(INTEGER, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(VARCHAR)
    short_title: Mapped[str | None] = mapped_column(VARCHAR(64))
    """ A shorter and constrained title for the collection """
    contact_user_id: Mapped[int | None] = mapped_column(INTEGER, ForeignKey("users.id"))
    citation: Mapped[str | None] = mapped_column(VARCHAR)
    license: Mapped[str | None] = mapped_column(VARCHAR(16))
    abstract: Mapped[str | None] = mapped_column(VARCHAR)
    description: Mapped[str | None] = mapped_column(VARCHAR)

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        projects: Mapped[List[Project]]
        contact_user: Mapped[User]
        provider_user: Mapped[User]
        users_by_role: Mapped[List["CollectionUserRole"]]
        organisations_by_role: Mapped[List["CollectionOrgaRole"]]

    def __str__(self) -> str:
        return "{0} ({1})".format(self.id, self.title)


# Unique index as we want no duplicate title
Index("CollectionTitle", Collection.__table__.c.title, unique=True)
Index("CollectionShortTitle", Collection.__table__.c.short_title, unique=True)


class CollectionProject(Model):
    __tablename__ = "collection_project"
    """ n<->n plain relationship b/w collection and projects """
    collection_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("collection.id"), primary_key=True)
    project_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("projects.projid"), primary_key=True)

    def __str__(self) -> str:
        return "{0},{1}".format(self.collection_id, self.project_id)


COLLECTION_ROLE_DATA_CREATOR = "C"
COLLECTION_ROLE_ASSOCIATED_PERSON = "A"
COLLECTION_ROLE_INSTITUTION_CODE_PROVIDER = "P"


class CollectionUserRole(Model):
    __tablename__ = "collection_user_role"
    """ n<->n valued (with role) relationship b/w collection and users """
    collection_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("collection.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(VARCHAR(1), primary_key=True)
    display_order: Mapped[int | None] = mapped_column(INTEGER)

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        collection: Mapped[Collection]
        user: Mapped[User]
        guest: Mapped[Guest]

    def __str__(self) -> str:
        return "{0},{1}:{2}".format(self.collection_id, self.user_id, self.role)


class CollectionOrgaRole(Model):
    __tablename__ = "collection_orga_role"
    """ n<->n valued relationship b/w collection and organisations """
    collection_id: Mapped[int] = mapped_column(INTEGER, ForeignKey("collection.id"), primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        INTEGER, ForeignKey("organizations.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(
        VARCHAR(1),  # 'C' for data Creator, 'A' for Associated 'person'
        primary_key=True,
    )
    display_order: Mapped[int | None] = mapped_column(INTEGER)

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        collection: Mapped[Collection]
        organization: Mapped[Organization]

    @property
    def organisation(self):
        return self.organization.name

    def __str__(self):
        return "{0},{1}:{2}".format(self.collection_id, self.organisation, self.role)
