# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# After SQL alchemy models are defined individually, setup the relations b/w them
#

if True:
    # Trick to prevent accidental re-export of the DB Models involved
    # Note: The trick doesn't work :(
    from .Acquisition import Acquisition
    from .CNNFeature import ObjectCNNFeature
    from .Collection import (
        Collection,
        CollectionProject,
        CollectionUserRole,
        CollectionOrgaRole,
    )
    from .Image import Image
    from .Job import Job
    from .Object import ObjectHeader, ObjectFields, ObjectsClassifHisto
    from .Process import Process
    from .Project import Project
    from .ProjectVariables import ProjectVariables
    from .ProjectPrivilege import ProjectPrivilege
    from .Sample import Sample
    from .Taxonomy import Taxonomy
    from .User import User, Role
    from .UserPreferences import UserPreferences
    from .Instrument import Instrument

    # noinspection PyUnresolvedReferences
    from .TaxoRecast import TaxoRecast

    # noinspection PyUnresolvedReferences
    from .WoRMs import WoRMS
    from .helpers.ORM import relationship

    # User
    User.roles = relationship(Role, secondary="users_roles")
    Role.users = relationship(User, secondary="users_roles", viewonly=True)

    # User preferences
    User.preferences_for_projects = relationship(UserPreferences, lazy="dynamic")

    # Collection
    Collection.projects = relationship(
        Project, secondary=CollectionProject.__tablename__
    )
    Collection.contact_user = relationship(
        User,
        foreign_keys=[Collection.contact_user_id],  # type:ignore # case2
        uselist=False,
    )
    Collection.provider_user = relationship(
        User,
        foreign_keys=[Collection.provider_user_id],  # type:ignore # case2
        uselist=False,
    )
    Collection.users_by_role = relationship(CollectionUserRole, viewonly=True)
    Collection.organisations_by_role = relationship(CollectionOrgaRole)

    CollectionUserRole.collection = relationship(Collection, uselist=False)
    CollectionUserRole.user = relationship(User, uselist=False)  # type:ignore # case2

    # Ancilliary to project
    ProjectVariables.project = relationship(
        Project, viewonly=True
    )  # type:ignore # case2
    Project.variables = relationship(ProjectVariables, uselist=False)

    # Project
    Project.all_samples = relationship(Sample, viewonly=True)
    Sample.project = relationship(Project)  # type:ignore # case2

    # Sample
    Sample.all_acquisitions = relationship(Acquisition, viewonly=True)
    Acquisition.sample = relationship(Sample)

    # Acquisition to its only Process
    Acquisition.process = relationship(Process, uselist=False)
    Process.acquisition = relationship(Acquisition, uselist=False, viewonly=True)

    # Privileges
    # Project.owner = relationship(User, primaryjoin="User.id==Project.owner_id",
    #                              foreign_keys="User.id", uselist=False)

    ProjectPrivilege.project = relationship(
        Project, cascade="all, delete-orphan", single_parent=True
    )
    Project.privs_for_members = relationship(ProjectPrivilege, viewonly=True)

    ProjectPrivilege.user = relationship(
        User, cascade="all, delete-orphan", single_parent=True
    )  # type:ignore # case2

    User.privs_on_projects = relationship(ProjectPrivilege, viewonly=True)

    Project.members = relationship(
        User, secondary=ProjectPrivilege.__tablename__, viewonly=True
    )
    Project.contact = relationship(
        User,
        secondary=ProjectPrivilege.__tablename__,
        secondaryjoin="and_(ProjectPrivilege.member == User.id, ProjectPrivilege.extra == 'C')",
        viewonly=True,
    )

    Project.instrument = relationship(Instrument, viewonly=True)
    # Object
    ObjectHeader.fields = relationship(
        ObjectFields, uselist=False, viewonly=True
    )  # type:ignore # case2
    ObjectFields.object = relationship(ObjectHeader, uselist=False)

    ObjectHeader.classif = relationship(
        Taxonomy,
        primaryjoin="Taxonomy.id==ObjectHeader.classif_id",
        foreign_keys="Taxonomy.id",
        uselist=False,
    )
    ObjectHeader.classifier = relationship(
        User,
        primaryjoin="User.id==ObjectHeader.classif_who",
        foreign_keys="User.id",
        uselist=False,
    )
    User.classified_objects = relationship(ObjectHeader)

    ObjectHeader.classif_auto = relationship(
        Taxonomy,
        primaryjoin="Taxonomy.id==foreign(ObjectHeader.classif_auto_id)",
        uselist=False,
    )

    ObjectCNNFeature.object = relationship(
        ObjectHeader,
        foreign_keys="ObjectHeader.objid",
        primaryjoin="ObjectCNNFeature.objcnnid==ObjectHeader.objid",
        uselist=False,
    )
    ObjectHeader.cnn_features = relationship(ObjectCNNFeature, uselist=False)

    ObjectHeader.all_images = relationship(Image)

    ObjectHeader.acquisition = relationship(Acquisition)
    Acquisition.all_objects = relationship(ObjectHeader, viewonly=True)

    ObjectHeader.history = relationship(ObjectsClassifHisto, viewonly=True)
    ObjectsClassifHisto.object = relationship(ObjectHeader)

    # Jobs
    Job.owner = relationship(User)
