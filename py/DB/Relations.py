# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# After SQL alchemy models are defined individually, setup the relations b/w them
#

from .Acquisition import Acquisition
from .Image import Image
# noinspection PyUnresolvedReferences
from .Object import Object, ObjectFields, ObjectCNNFeature
from .Process import Process
from .Project import Project
from .Sample import Sample
# noinspection PyUnresolvedReferences
from .Taxonomy import *
from .User import *

Project.all_objects = relationship(Object)
Object.project = relationship(Project)

Project.all_samples = relationship(Sample)
Sample.project = relationship(Project)

Project.all_processes = relationship(Process)
Process.project = relationship(Project)

Project.all_acquisitions = relationship(Acquisition)
Acquisition.project = relationship(Project)

Object.fields = relationship(ObjectFields, uselist=False)
ObjectFields.object = relationship(Object, uselist=False)

Object.img0 = relationship(Image, foreign_keys=Image.objid)
Object.all_images = relationship(Image)

Object.sample = relationship(Sample)
Sample.all_objects = relationship(Object)

Object.acquisition = relationship(Acquisition)
Acquisition.all_objects = relationship(Object)

Object.process = relationship(Process)
Process.all_objects = relationship(Object)
