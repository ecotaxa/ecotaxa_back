# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from sqlalchemy import Column, Sequence, ForeignKey, Index
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER
from sqlalchemy.orm import relationship

# Circular dependency
# from DB.Project import Project
from .helpers.ORM import Model


class ProjectPrivilege(Model):
    """
        What users can do on a project.
        Is an Association object, @see https://docs.sqlalchemy.org/en/13/orm/basic_relationships.html#association-object
    """
    __tablename__ = 'projectspriv'
    # TODO: Isn't there a natural PK with all columns?
    id = Column(INTEGER, Sequence('seq_projectspriv'), primary_key=True)

    # links
    projid = Column(INTEGER, ForeignKey('projects.projid', ondelete="CASCADE"), nullable=False)
    # TODO: Same as project: if a user is gone, no interest in keeping its privileges.
    # OTOH we don't so far (17 Aug 2020) delete users.
    member = Column(INTEGER, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)

    # association value
    privilege = Column(VARCHAR(255), nullable=False)

    # relationships
    # The relationships are created in Relations.py but the typing here helps the IDE
    project: relationship
    user: relationship

    def __str__(self):
        return "{0} ({1})".format(self.member, self.privilege)


Index('IS_ProjectsPriv', ProjectPrivilege.projid, ProjectPrivilege.member, unique=True)
