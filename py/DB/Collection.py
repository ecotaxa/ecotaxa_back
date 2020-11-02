# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Collection i.e. set of projects.
#
from sqlalchemy import Column, Sequence, ForeignKey, Index
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER
from sqlalchemy.orm import relationship

from DB.helpers.ORM import Model


class Collection(Model):
    """ A set of projects see #82, #335, #519 """
    __tablename__ = 'collection'
    id = Column(INTEGER, Sequence('seq_collection'), primary_key=True)
    title = Column(VARCHAR, nullable=False)
    contact_user_id = Column(INTEGER, ForeignKey('users.id'))
    citation = Column(VARCHAR)
    license = Column(VARCHAR(16))
    abstract = Column(VARCHAR)
    description = Column(VARCHAR)

    # The relationships are created in Relations.py but the typing here helps IDE
    projects: relationship
    contact_user: relationship
    users: relationship

    def __str__(self):
        return "{0} ({1})".format(self.id, self.title)


# Unique index as we want no duplicate title
Index('CollectionTitle', Collection.__table__.c.title, unique=True)


class CollectionProject(Model):
    __tablename__ = 'collection_project'
    """ n<->n plain relationship b/w collection and projects """
    collection_id = Column(INTEGER, ForeignKey('collection.id'), primary_key=True)
    project_id = Column(INTEGER, ForeignKey('projects.projid'), primary_key=True)

    def __str__(self):
        return "{0},{1}".format(self.collection_id, self.project_id)


COLLECTION_ROLE_DATA_CREATOR = "C"
COLLECTION_ROLE_ASSOCIATED_PERSON = "A"


class CollectionUserRole(Model):
    __tablename__ = 'collection_user_role'
    """ n<->n valued (with role) relationship b/w collection and users """
    collection_id = Column(INTEGER, ForeignKey('collection.id'), primary_key=True)
    user_id = Column(INTEGER, ForeignKey('users.id'), primary_key=True)
    role = Column(VARCHAR(1), nullable=False, primary_key=True)

    # The relationships are created in Relations.py but the typing here helps IDE
    collection: relationship
    user: relationship

    def __str__(self):
        return "{0},{1}:{2}".format(self.collection_id, self.user_id, self.role)
