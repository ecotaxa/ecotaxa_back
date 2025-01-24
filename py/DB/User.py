# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from __future__ import annotations

from enum import Enum
from typing import Iterable, TYPE_CHECKING, Union

from sqlalchemy import event, SmallInteger
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.engine import Connection

from data.Countries import countries_by_name
from .helpers.DDL import (
    Column,
    ForeignKey,
    Sequence,
    Integer,
    String,
    Boolean,
)
from .helpers.Direct import text, func
from .helpers.ORM import Model, relationship, Insert
from .helpers.Postgres import TIMESTAMP, VARCHAR

NO_ORGANIZATION_ADDED = "Error adding organization name"

if TYPE_CHECKING:
    from .ProjectPrivilege import ProjectPrivilege


class UserStatus(int, Enum):
    blocked: Final = -1
    inactive: Final = 0
    active: Final = 1
    pending: Final = 2


class UserType(str, Enum):
    guest: Final = "guest"
    user: Final = "user"


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


class Person(Model):
    __tablename__ = "users"
    id: int = Column(Integer, Sequence("seq_users"), primary_key=True)
    email: str = Column(String(255), unique=True, nullable=False)
    name: str = Column(String(255), nullable=False)
    country: str = Column(String(50))
    orcid: str = Column(String(20), nullable=True)
    type = Column(String(10))
    usercreationdate = Column(TIMESTAMP, default=func.now())
    organisation = Column(VARCHAR, ForeignKey("organizations.name"), nullable=False)
    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": "person",
    }

    def __str__(self):
        return "{0} ({1})".format(self.name, self.email)


class Guest(Person):
    __mapper_args__ = {
        "polymorphic_identity": "guest",
    }


class User(Person):
    password: str = Column(String(255))
    status: int = Column(SmallInteger(), default=1)
    status_date = Column(TIMESTAMP)
    status_admin_comment: str = Column(String(255))
    preferences: str = Column(String(40000))
    usercreationreason = Column(String(1000))
    # Mail status: True for verified, default NULL
    mail_status: bool = Column(Boolean(), nullable=True)
    # Date the mail status was set
    mail_status_date = Column(
        TIMESTAMP
    )  # The relationships are created in Relations.py but the typing here helps the IDE

    roles: relationship
    # The projects that user has rights in, so he/she can participate at various levels.
    privs_on_projects: Iterable[ProjectPrivilege]
    # The objects of which _present_ classification was done by the user
    classified_objects: relationship
    # Preferences, per project, the global ones kept in field above.
    preferences_for_projects: relationship
    __mapper_args__ = {
        "polymorphic_identity": "user",
    }

    def has_role(self, role: str) -> bool:
        # TODO: Cache a bit. All roles are just python objects due to SQLAlchemy magic.
        return role in [r.name for r in list(self.roles)]


# associate the listener function with SomeClass,
# to execute during the "before_insert" hook
@event.listens_for(User, "before_insert")
@event.listens_for(Guest, "before_insert")
@event.listens_for(User, "before_update")
@event.listens_for(Guest, "before_update")
def my_before_person_organisation(mapper, connection: Connection, target):
    # Ensure there is always an org for any Person
    value = target.organisation.strip()
    org: Union[str, None]
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
    except Exception as e:
        pass
    target.organisation = target.organisation.strip()
    assert org is not None, NO_ORGANIZATION_ADDED


class Role(Model):
    """
    The roles granted to users.
    """

    __tablename__ = "roles"
    id = Column(Integer(), primary_key=True)  # ,Sequence('seq_roles')
    name = Column(String(80), unique=True, nullable=False)
    # The relationships are created in Relations.py but the typing here helps the IDE
    users: relationship

    APP_ADMINISTRATOR = "Application Administrator"
    USERS_ADMINISTRATOR = "Users Administrator"

    # Existing data references them by id, so changing the order here will scramble rights completely!
    ALL_ROLES = [APP_ADMINISTRATOR, USERS_ADMINISTRATOR]

    #    description = Column(String(255))
    def __str__(self):
        return "{0} ({1})".format(self.name, self.id)


@event.listens_for(Role.__table__, "after_create")
def insert_initial_role_values(_table, sess, **kwargs):
    """
    Create default roles without granting them to anyone.
    """
    for role_id, a_role in enumerate(Role.ALL_ROLES, 1):
        ins = Insert(Role).values((role_id, a_role))
        sess.execute(ins)


class UserRole(Model):
    """
    Many-to-many relationship b/w User and Roles.
    """

    __tablename__ = "users_roles"
    user_id = Column(Integer(), ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer(), ForeignKey("roles.id"), primary_key=True)


class Country(Model):
    """
    TODO: There is no FK from users
    """

    __tablename__ = "countrylist"
    countryname = Column(String(50), primary_key=True, nullable=False)


@event.listens_for(Country.__table__, "after_create")
def insert_initial_country_values(_table, sess, **kwargs):
    """
    Create default countries after table creation.
    """
    for a_country in countries_by_name.keys():
        ins = Insert(Country).values((a_country,))
        sess.execute(ins)


class TempPasswordReset(Model):
    """
    store temporary uuid when a reset password is in progress
    """

    __tablename__ = "user_password_reset"
    user_id = Column(
        Integer(),
        ForeignKey(
            "users.id", name="user_password_reset_user_id_fkey", ondelete="CASCADE"
        ),
        primary_key=True,
    )
    temp_password = Column(String(255), nullable=False)
    creation_date = Column(TIMESTAMP, default=func.now(), nullable=False)
