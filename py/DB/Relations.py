# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# After SQL alchemy models are defined individually, setup the relations b/w them
#

from .Acquisition import Acquisition
from .Collection import Collection, CollectionProject, CollectionUserRole, CollectionOrgaRole
from .Image import Image
from .Job import Job
from .Object import ObjectHeader, ObjectFields, ObjectCNNFeature, ObjectsClassifHisto
# Particle project
from .ParticleProject import ParticleProject, ParticleSample
from .Process import Process
from .Project import Project
from .ProjectPrivilege import ProjectPrivilege
from .Sample import Sample
from .Task import Task
from .Taxonomy import Taxonomy
from .User import User, Role
from .UserPreferences import UserPreferences
# noinspection PyUnresolvedReferences
from .WoRMs import WoRMS
from .helpers.ORM import relationship

# User
User.roles = relationship(Role, secondary="users_roles")
Role.users = relationship(User, secondary="users_roles", viewonly=True)

# User preferences
User.preferences_for_projects = relationship(UserPreferences, lazy='dynamic')

# Collection
Collection.projects = relationship(Project, secondary=CollectionProject.__tablename__)
Collection.contact_user = relationship(User, foreign_keys=[Collection.contact_user_id], uselist=False)
Collection.provider_user = relationship(User, foreign_keys=[Collection.provider_user_id], uselist=False)
Collection.users_by_role = relationship(CollectionUserRole, viewonly=True)
Collection.organisations_by_role = relationship(CollectionOrgaRole)

CollectionUserRole.collection = relationship(Collection, uselist=False)
CollectionUserRole.user = relationship(User, uselist=False)

# Project
Project.all_samples = relationship(Sample, viewonly=True)
Sample.project = relationship(Project)

# Sample
Sample.all_acquisitions = relationship(Acquisition, viewonly=True)
Acquisition.sample = relationship(Sample)

# Acquisition to its only Process
Acquisition.process = relationship(Process, uselist=False)
Process.acquisition = relationship(Acquisition, uselist=False, viewonly=True)

# Privileges
# Project.owner = relationship(User, primaryjoin="User.id==Project.owner_id",
#                              foreign_keys="User.id", uselist=False)

ProjectPrivilege.project = relationship(Project, cascade="all, delete-orphan", single_parent=True)
Project.privs_for_members = relationship(ProjectPrivilege, viewonly=True)

ProjectPrivilege.user = relationship(User, cascade="all, delete-orphan", single_parent=True)
User.privs_on_projects = relationship(ProjectPrivilege, viewonly=True, )

# Object
ObjectHeader.fields = relationship(ObjectFields, uselist=False, viewonly=True)
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

ObjectHeader.all_images = relationship(Image)

ObjectHeader.acquisition = relationship(Acquisition)
Acquisition.all_objects = relationship(ObjectHeader, viewonly=True)

ObjectHeader.history = relationship(ObjectsClassifHisto, viewonly=True)
ObjectsClassifHisto.object = relationship(ObjectHeader)
# Task
Task.owner = relationship(User)

# Particle Project
ParticleProject.ecotaxa_project = relationship(Project)
Project.ecopart_project = relationship(ParticleProject, viewonly=True)

# Particle Sample
ParticleSample.ecotaxa_sample = relationship(Sample)
Sample.ecopart_sample = relationship(ParticleSample, viewonly=True)

# Jobs
Job.owner = relationship(User)