# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from sqlalchemy import Column, Sequence, ForeignKey, Index
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER
from sqlalchemy.orm import relationship, backref

# Circular dependency
# from DB.Project import Project
from .User import User
from .helpers.ORM import Model

MANAGE = 'Manage'


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
    project = relationship('Project', backref=backref('privs_for_members',
                                                      cascade="all, delete-orphan",
                                                      single_parent=True))
    user = relationship(User, backref=backref('privs_on_projects',
                                              cascade="all, delete-orphan",
                                              single_parent=True))

    def __str__(self):
        return "{0} ({1})".format(self.member, self.privilege)

    @classmethod
    def managers_by_project(cls) -> str:
        """
            Return SQL chunk for all managers for all projects.
        """
        return """ SELECT u.email, u.name, pp.projid, rank() 
                     OVER (PARTITION BY pp.projid ORDER BY pp.id) rang
                     FROM projectspriv pp 
                     JOIN users u ON pp.member = u.id
                    WHERE pp.privilege = '""" + MANAGE + """' 
                      AND u.active = true """

    @classmethod
    def first_manager_by_project(cls) -> str:
        """
            Return SQL chunk for historically first manager for all projects.
        """
        return """ SELECT * from ( """ + ProjectPrivilege.managers_by_project() + """ ) qpp 
                    WHERE rang = 1 """


Index('IS_ProjectsPriv', ProjectPrivilege.projid, ProjectPrivilege.member, unique=True)
