# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import TYPE_CHECKING

from sqlalchemy.orm import mapped_column

from .helpers.DDL import Sequence, ForeignKey, Index
from .helpers.ORM import Model, Mapped
from .helpers.Postgres import VARCHAR, INTEGER

if TYPE_CHECKING:
    from .Project import Project
    from .User import User
# from .Project import Project


class ProjectPrivilege(Model):
    """
    What users can do on a project.
    Is an Association object, @see https://docs.sqlalchemy.org/en/13/orm/basic_relationships.html#association-object
    """

    __tablename__ = "projectspriv"
    # TODO: Isn't there a natural PK with all columns?
    id: Mapped[int] = mapped_column(
        INTEGER, Sequence("seq_projectspriv"), primary_key=True
    )

    # links
    projid: Mapped[int] = mapped_column(
        INTEGER, ForeignKey("projects.projid", ondelete="CASCADE")
    )
    # TODO: Same as project: if a user is gone, no interest in keeping its privileges.
    # OTOH we don't so far (17 Aug 2020) delete users.
    member: Mapped[int] = mapped_column(
        INTEGER, ForeignKey("users.id", ondelete="CASCADE")
    )

    # association value
    privilege: Mapped[str] = mapped_column(VARCHAR(255))
    # complement of the privilege, so far just 'C' for Contact who is a manager
    extra: Mapped[str | None] = mapped_column(VARCHAR(1))

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        project: Mapped[Project]
        user: Mapped[User]

    def __str__(self):
        return "{0} ({1})".format(self.member, self.privilege)


Index("IS_ProjectsPriv", ProjectPrivilege.projid, ProjectPrivilege.member, unique=True)
