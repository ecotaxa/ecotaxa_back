# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# After SQL alchemy models are defined individually, setup the relations b/w them
#

if True:
    # Trick to prevent accidental re-export of the DB Models involved
    # Note: The trick doesn't work :(
    from .CNNFeatureVector import ObjectCNNFeatureVector
    from .Collection import (
        CollectionUserRole,
        CollectionOrgaRole,
    )
    from .Object import ObjectHeader, ObjectsClassifHisto
    from .User import User, Guest

    # noinspection PyUnresolvedReferences
    from .TaxoRecast import TaxoRecast

    from .Training import Training

    from .helpers.ORM import relationship

    # User
    # User.roles = relationship(Role, secondary="users_roles")
    # Role.users = relationship(User, secondary="users_roles", viewonly=True)

    # User preferences
    # User.preferences_for_projects = relationship(UserPreferences, lazy="dynamic")
    # User organization
    User.organization = relationship("Organization", uselist=False, lazy="joined")
    # Guest organization
    Guest.organization = relationship("Organization", uselist=False, lazy="joined")
    # Collection
    # Collection.projects = relationship(
    #     Project, secondary=CollectionProject.__tablename__
    # )
    # Collection.contact_user = relationship(
    #     User,
    #     foreign_keys=[Collection.contact_user_id],
    #     uselist=False,
    # )
    # Collection.provider_user = relationship(
    #     User,
    #     foreign_keys=[Collection.provider_user_id],
    #     uselist=False,
    # )
    # Collection.users_by_role = relationship(CollectionUserRole, viewonly=True)
    # Collection.organisations_by_role = relationship(CollectionOrgaRole, viewonly=True)

    # CollectionUserRole.collection = relationship(Collection, uselist=False)
    # CollectionUserRole.user = relationship(User, uselist=False)
    CollectionUserRole.guest = relationship("Guest", uselist=False)  # type: ignore # case2
    CollectionOrgaRole.collection = relationship("Collection", uselist=False)
    CollectionOrgaRole.organization = relationship(
        "Organization", uselist=False, lazy="joined"
    )  # type: ignore # case2
    # Ancilliary to project
    # ProjectVariables.project = relationship(Project, viewonly=True)
    # Project.variables = relationship(ProjectVariables, uselist=False)

    # Project
    # Project.all_samples = relationship(Sample, viewonly=True)
    # Sample.project = relationship(Project)

    # Sample
    # Sample.all_acquisitions = relationship(Acquisition, viewonly=True)
    # Acquisition.sample = relationship(Sample)

    # Acquisition to its only Process
    # Acquisition.process = relationship(Process, uselist=False)
    # Process.acquisition = relationship(Acquisition, uselist=False, viewonly=True)

    # Privileges
    # Project.owner = relationship(User, primaryjoin="User.id==Project.owner_id",
    #                              foreign_keys="User.id", uselist=False)

    # ProjectPrivilege.project = relationship(
    #     Project, cascade="all, delete-orphan", single_parent=True
    # )
    # Project.privs_for_members = relationship(ProjectPrivilege, viewonly=True)

    # ProjectPrivilege.user = relationship(
    #     User, cascade="all, delete-orphan", single_parent=True
    # )
    # User.privs_on_projects = relationship(ProjectPrivilege, viewonly=True)

    # Project.members = relationship(
    #     User, secondary=ProjectPrivilege.__tablename__, viewonly=True
    # )

    # Project.instrument = relationship(Instrument, viewonly=True)
    # Object
    # ObjectHeader.fields = relationship(ObjectFields, uselist=False, viewonly=True)
    # ObjectFields.object = relationship(ObjectHeader, uselist=False)

    # ObjectHeader.classif = relationship(
    #     Taxonomy,
    #     primaryjoin="Taxonomy.id==ObjectHeader.classif_id",
    #     foreign_keys="Taxonomy.id",
    #     uselist=False,
    # )
    # ObjectHeader.classifier = relationship(
    #     User,
    #     primaryjoin="User.id==ObjectHeader.classif_who",
    #     foreign_keys="User.id",
    #     uselist=False,
    # )
    # User.classified_objects = relationship(ObjectHeader)

    ObjectCNNFeatureVector.object = relationship(
        "ObjectHeader",
        foreign_keys="ObjectHeader.objid",
        primaryjoin="ObjectCNNFeatureVector.objcnnid==ObjectHeader.objid",
        uselist=False,
    )

    ObjectHeader.cnn_features = relationship("ObjectCNNFeatureVector", uselist=False)

    # ObjectHeader.all_images = relationship(Image)

    # ObjectHeader.acquisition = relationship(Acquisition)
    # Acquisition.all_objects = relationship(ObjectHeader, viewonly=True)

    # ObjectHeader.history = relationship(ObjectsClassifHisto, viewonly=True)
    # ObjectsClassifHisto.object = relationship(ObjectHeader)

    Training.predictions = relationship("Prediction", passive_deletes=True)
    Training.project = relationship(
        "Project",
    )

    ObjectsClassifHisto.classif = relationship("Taxonomy")
    ObjectsClassifHisto.classifier = relationship("User")

    # Jobs
    # Job.owner = relationship(User)
