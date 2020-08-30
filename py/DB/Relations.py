# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# After SQL alchemy models are defined individually, setup the relations b/w them
#
from sqlalchemy import and_

from .Acquisition import Acquisition
from .Image import Image
from .Object import ObjectHeader, ObjectFields, ObjectCNNFeature
# Particle project
from .ParticleProject import ParticleProject
from .Process import Process
from .Project import Project
from .ProjectPrivilege import ProjectPrivilege
from .Sample import Sample
from .Task import Task
from .Taxonomy import Taxonomy
from .User import User, Role
from .helpers.ORM import relationship

# User
User.roles = relationship(Role, secondary="users_roles")
Role.users = relationship(User, secondary="users_roles")

# Project
Project.all_objects = relationship(ObjectHeader)
ObjectHeader.project = relationship(Project)

Project.all_samples = relationship(Sample, lazy="raise_on_sql")
Sample.project = relationship(Project)

Project.all_acquisitions = relationship(Acquisition, lazy="raise_on_sql")
Acquisition.project = relationship(Project)

Project.all_processes = relationship(Process, lazy="raise_on_sql")
Process.project = relationship(Project)

# Sample
# This is a temporary join until the DB evolves
Sample.all_acquisitions = relationship(Acquisition, viewonly=True, lazy="raise_on_sql",
                                       secondary=ObjectHeader.__tablename__,
                                       secondaryjoin=and_(ObjectHeader.projid == Acquisition.projid,
                                                          ObjectHeader.acquisid == Acquisition.acquisid))

# Acquisition
# This is a temporary join until the DB evolves
Acquisition.all_processes = relationship(Process, viewonly=True, lazy="raise_on_sql",
                                         secondary=ObjectHeader.__tablename__,
                                         secondaryjoin=and_(ObjectHeader.projid == Process.projid,
                                                            ObjectHeader.processid == Process.processid))

# Process
Process.all_objects = relationship(ObjectHeader)

# Privileges
ProjectPrivilege.project = relationship(Project, cascade="all, delete-orphan", single_parent=True)
Project.privs_for_members = relationship(ProjectPrivilege)

ProjectPrivilege.user = relationship(User, cascade="all, delete-orphan", single_parent=True)
User.privs_on_projects = relationship(ProjectPrivilege)

# Object
ObjectHeader.fields = relationship(ObjectFields, uselist=False)
ObjectFields.object = relationship(ObjectHeader, uselist=False)

ObjectHeader.classif = relationship(Taxonomy, primaryjoin="Taxonomy.id==ObjectHeader.classif_id",
                                    foreign_keys="Taxonomy.id", uselist=False)
ObjectHeader.classifier = relationship(User, primaryjoin="User.id==ObjectHeader.classif_who", foreign_keys="User.id",
                                       uselist=False)
User.classified_objects = relationship(ObjectHeader)

ObjectHeader.classif_auto = relationship(Taxonomy, primaryjoin="Taxonomy.id==foreign(ObjectHeader.classif_auto_id)",
                                         uselist=False)

ObjectCNNFeature.object = relationship(ObjectHeader, foreign_keys="ObjectHeader.objid",
                                       primaryjoin="ObjectCNNFeature.objcnnid==ObjectHeader.objid", uselist=False)
ObjectHeader.cnn_features = relationship(ObjectCNNFeature, uselist=False)

ObjectHeader.img0 = relationship(Image, foreign_keys=Image.objid)
ObjectHeader.all_images = relationship(Image)

ObjectHeader.sample = relationship(Sample)
Sample.all_objects = relationship(ObjectHeader)

ObjectHeader.acquisition = relationship(Acquisition)
Acquisition.all_objects = relationship(ObjectHeader)

ObjectHeader.process = relationship(Process)

# Task
Task.owner = relationship(User)

# Particle Project
ParticleProject.ecotaxa_project = relationship(Project)
Project.ecopart_project = relationship(ParticleProject)
