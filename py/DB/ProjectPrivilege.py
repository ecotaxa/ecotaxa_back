# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from __future__ import annotations

from typing import TYPE_CHECKING

from .helpers.DDL import Column, Sequence, ForeignKey, Index
from .helpers.ORM import Model
from .helpers.ORM import relationship
from .helpers.Postgres import VARCHAR, INTEGER

if TYPE_CHECKING:
    from .User import User


class ProjectPrivilege(Model):
    """
    What users can do on a project.
    Is an Association object, @see https://docs.sqlalchemy.org/en/13/orm/basic_relationships.html#association-object
    """

    __tablename__ = "projectspriv"
    # TODO: Isn't there a natural PK with all columns?
    id: int = Column(INTEGER, Sequence("seq_projectspriv"), primary_key=True)

    # links
    projid: int = Column(
        INTEGER, ForeignKey("projects.projid", ondelete="CASCADE"), nullable=False
    )
    # TODO: Same as project: if a user is gone, no interest in keeping its privileges.
    # OTOH we don't so far (17 Aug 2020) delete users.
    member: int = Column(
        INTEGER, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # association value
    privilege = Column(VARCHAR(255), nullable=False)
    # complement of the privilege, so far just 'C' for Contact who is a manager
    extra = Column(VARCHAR(1), nullable=True)

    # relationships
    # The relationships are created in Relations.py but the typing here helps the IDE
    project: relationship
    user: User

    def __str__(self):
        return "{0} ({1})".format(self.member, self.privilege)


Index("IS_ProjectsPriv", ProjectPrivilege.projid, ProjectPrivilege.member, unique=True)
