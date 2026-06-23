# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Collection i.e. set of projects.
#
from __future__ import annotations

from typing import TYPE_CHECKING

from DB.helpers.ORM import Model, relationship
from .helpers.DDL import Column, Sequence, ForeignKey, Index
from .helpers.Postgres import VARCHAR, INTEGER

if TYPE_CHECKING:
    pass
else:
    Project = "Project"


class CollectionProject(Model):
    __tablename__ = "collection_project"
    """ n<->n plain relationship b/w collection and projects """
    collection_id: int = Column(INTEGER, ForeignKey("collection.id"), primary_key=True)
    project_id: int = Column(INTEGER, ForeignKey("projects.projid"), primary_key=True)

    def __str__(self) -> str:
        return "{0},{1}".format(self.collection_id, self.project_id)


class Collection(Model):
    """A set of projects see #82, #335, #519"""

    __tablename__ = "collection"
    id: int = Column(INTEGER, Sequence("collection_id_seq"), primary_key=True)
    """ Internal identifier """
    external_id: str = Column(VARCHAR, nullable=False)
    """ External identifier, e.g. doi:10.xxxx/eml.1.1 """
    external_id_system: str = Column(VARCHAR, nullable=False)
    """ External identifier system, e.g. https://doi.org """
    provider_user_id = Column(INTEGER, ForeignKey("users.id"))
    title: str = Column(VARCHAR, nullable=False)
    short_title = Column(VARCHAR(64))
    """ A shorter and constrained title for the collection """
    contact_user_id = Column(INTEGER, ForeignKey("users.id"))
    citation = Column(VARCHAR)
    license = Column(VARCHAR(16))
    abstract = Column(VARCHAR)
    description = Column(VARCHAR)

    # The relationships are created in Relations.py but the typing here helps IDE
    projects = relationship("Project", secondary=CollectionProject.__tablename__)
    contact_user = relationship(
        "User",
        foreign_keys="Collection.contact_user_id",
        uselist=False,
    )
    provider_user = relationship(
        "User",
        foreign_keys="Collection.provider_user_id",
        uselist=False,
    )
    users_by_role = relationship("CollectionUserRole", viewonly=True)
    organisations_by_role = relationship(
        "CollectionOrgaRole"
    )  # TODO: Repeat should not be needed, mypy bug

    def __str__(self) -> str:
        return "{0} ({1})".format(self.id, self.title)


# Unique index as we want no duplicate title
Index("CollectionTitle", Collection.__table__.c.title, unique=True)
Index("CollectionShortTitle", Collection.__table__.c.short_title, unique=True)

COLLECTION_ROLE_DATA_CREATOR = "C"
COLLECTION_ROLE_ASSOCIATED_PERSON = "A"
COLLECTION_ROLE_INSTITUTION_CODE_PROVIDER = "P"


class CollectionUserRole(Model):
    __tablename__ = "collection_user_role"
    """ n<->n valued (with role) relationship b/w collection and users """
    collection_id: int = Column(INTEGER, ForeignKey("collection.id"), primary_key=True)
    user_id: int = Column(INTEGER, ForeignKey("users.id"), primary_key=True)
    role: str = Column(VARCHAR(1), nullable=False, primary_key=True)

    # Relationships
    collection = relationship("Collection", uselist=False)
    user = relationship("User", uselist=False)
    display_order: int = Column(INTEGER)
    # The relationships are created in Relations.py but the typing here helps IDE
    guest = relationship("Guest")

    def __str__(self) -> str:
        return "{0},{1}:{2}".format(self.collection_id, self.user_id, self.role)


class CollectionOrgaRole(Model):
    __tablename__ = "collection_orga_role"
    """ n<->n valued relationship b/w collection and organisations """
    collection_id: int = Column(INTEGER, ForeignKey("collection.id"), primary_key=True)
    organization_id: str = Column(
        INTEGER, ForeignKey("organizations.id"), nullable=False, primary_key=True
    )
    collection = relationship("Collection")
    organization = relationship("Organization")
    role: str = Column(
        VARCHAR(1),  # 'C' for data Creator, 'A' for Associated 'person'
        nullable=False,
        primary_key=True,
    )
    display_order: int = Column(INTEGER)

    @property
    def organisation(self):
        return self.organization.name

    def __str__(self):
        return "{0},{1}:{2}".format(self.collection_id, self.organisation, self.role)
