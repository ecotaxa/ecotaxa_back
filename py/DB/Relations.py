# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# After SQL alchemy models are defined individually, setup the relations b/w them
#
from .Acquisition import Acquisition
from .Image import Image
from .Object import Object, ObjectFields, ObjectCNNFeature
from .Process import Process
from .Project import Project
from .ProjectPrivilege import ProjectPrivilege
from .Sample import Sample
from .Taxonomy import Taxonomy
from .User import User, Role
from .helpers.ORM import relationship
# Particle project
from .ParticleProject import ParticleProject

# User
User.roles = relationship(Role, secondary="users_roles")
Role.users = relationship(User, secondary="users_roles")

# Project
Project.all_objects = relationship(Object)
Object.project = relationship(Project)

Project.all_samples = relationship(Sample)
Sample.project = relationship(Project)

Project.all_processes = relationship(Process)
Process.project = relationship(Project)

Project.all_acquisitions = relationship(Acquisition)
Acquisition.project = relationship(Project)

# Privileges
ProjectPrivilege.project = relationship(Project, cascade="all, delete-orphan", single_parent=True)
Project.privs_for_members = relationship(ProjectPrivilege)

ProjectPrivilege.user = relationship(User, cascade="all, delete-orphan", single_parent=True)
User.privs_on_projects = relationship(ProjectPrivilege)

# Object
Object.fields = relationship(ObjectFields, uselist=False)
ObjectFields.object = relationship(Object, uselist=False)

Object.classif = relationship(Taxonomy, primaryjoin="Taxonomy.id==Object.classif_id",
                              foreign_keys="Taxonomy.id", uselist=False)
Object.classifier = relationship(User, primaryjoin="User.id==Object.classif_who", foreign_keys="User.id",
                                 uselist=False, )
User.classified_objects = relationship(Object)

Object.classif_auto = relationship(Taxonomy, primaryjoin="Taxonomy.id==foreign(Object.classif_auto_id)",
                                   uselist=False, )

ObjectCNNFeature.object = relationship(Object, foreign_keys="Object.objid",
                                       primaryjoin="ObjectCNNFeature.objcnnid==Object.objid", uselist=False)
Object.cnn_features = relationship(ObjectCNNFeature)

Object.img0 = relationship(Image, foreign_keys=Image.objid)
Object.all_images = relationship(Image)

Object.sample = relationship(Sample)
Sample.all_objects = relationship(Object)

Object.acquisition = relationship(Acquisition)
Acquisition.all_objects = relationship(Object)

Object.process = relationship(Process)
Process.all_objects = relationship(Object)

# Particle Project
ParticleProject.ecotaxa_project=relationship(Project)
Project.ecopart_project=relationship(ParticleProject)
