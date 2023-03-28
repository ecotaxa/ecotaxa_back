# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Collection i.e. set of projects.
#
from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Iterable

from DB.helpers.ORM import Model
from .helpers.DDL import Column, Sequence, ForeignKey, Index
from .helpers.ORM import relationship
from .helpers.Postgres import VARCHAR, INTEGER

if TYPE_CHECKING:
    from .User import User


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
    projects: relationship
    contact_user: Optional[User]
    provider_user: Optional[User]
    users_by_role: Iterable["CollectionUserRole"]
    organisations_by_role: Iterable["CollectionOrgaRole"]

    def __str__(self) -> str:
        return "{0} ({1})".format(self.id, self.title)


# Unique index as we want no duplicate title
Index("CollectionTitle", Collection.__table__.c.title, unique=True)
Index("CollectionShortTitle", Collection.__table__.c.short_title, unique=True)


class CollectionProject(Model):
    __tablename__ = "collection_project"
    """ n<->n plain relationship b/w collection and projects """
    collection_id = Column(INTEGER, ForeignKey("collection.id"), primary_key=True)
    project_id = Column(INTEGER, ForeignKey("projects.projid"), primary_key=True)

    def __str__(self) -> str:
        return "{0},{1}".format(self.collection_id, self.project_id)


COLLECTION_ROLE_DATA_CREATOR = "C"
COLLECTION_ROLE_ASSOCIATED_PERSON = "A"


class CollectionUserRole(Model):
    __tablename__ = "collection_user_role"
    """ n<->n valued (with role) relationship b/w collection and users """
    collection_id: int = Column(INTEGER, ForeignKey("collection.id"), primary_key=True)
    user_id: int = Column(INTEGER, ForeignKey("users.id"), primary_key=True)
    role: str = Column(VARCHAR(1), nullable=False, primary_key=True)

    # The relationships are created in Relations.py but the typing here helps IDE
    collection: relationship
    user: User

    def __str__(self) -> str:
        return "{0},{1}:{2}".format(self.collection_id, self.user_id, self.role)


class CollectionOrgaRole(Model):
    __tablename__ = "collection_orga_role"
    """ n<->n valued relationship b/w collection and organisations """
    collection_id: int = Column(INTEGER, ForeignKey("collection.id"), primary_key=True)
    organisation: str = Column(VARCHAR(255), primary_key=True)
    role: str = Column(
        VARCHAR(1),  # 'C' for data Creator, 'A' for Associated 'person'
        nullable=False,
        primary_key=True,
    )

    def __str__(self):
        return "{0},{1}:{2}".format(self.collection_id, self.organisation, self.role)
