# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from __future__ import annotations

from typing import Union
from enum import Enum
from sqlalchemy import event

from sqlalchemy.engine import Connection
from sqlalchemy.dialects.postgresql import ARRAY
from .helpers.DDL import (
    Column,
    ForeignKey,
    Integer,
    String,
)
from .helpers.Direct import text, func
from .helpers.ORM import Model, relationship

NO_ORGANIZATION_ADDED = "Error adding organization name"


class PeopleOrganizationDirectory(str, Enum):
    orcid: Final = "https://orcid.org/"
    edmo: Final = "https://edmo.seadatanet.org/"


class Organization(Model):
    __tablename__ = "organizations"
    name: str = Column(String(512), unique=True, primary_key=True)
    directories: list = Column(ARRAY(String), nullable=True)
    persons = relationship("Person")
    users = relationship("User", viewonly=True, overlaps="persons")
    guests = relationship("Guest", viewonly=True, overlaps="persons")

    def __str__(self):
        return "{0} ({1})".format(self.name, self.directories)


def my_before_organization(mapper, connection: Connection, target):
    # Ensure there is always an org for any Person
    value = target.organisation.strip()
    org: Union[str, None] = None
    try:
        org = connection.execute(
            text("select name from organizations WHERE name ilike :nam "),
            {"nam": value},
        ).scalar()
        if org is None:
            org = connection.execute(
                text("insert into organizations(name) values(:nam) RETURNING name"),
                {"nam": value},
            ).scalar()
    except:
        pass
    target.organisation = target.organisation.strip()
    assert org is not None, NO_ORGANIZATION_ADDED
