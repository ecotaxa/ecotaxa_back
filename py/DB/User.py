# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List

from sqlalchemy.orm import mapped_column

from data.Countries import countries_by_name
from .helpers.DDL import (
    Boolean,
    ForeignKey,
    Integer,
    Sequence,
    String,
)
from .helpers.Direct import func
from .helpers.ORM import Insert, Mapped, SmallInteger, event, Model
from .helpers.Postgres import INTEGER, TIMESTAMP

if TYPE_CHECKING:
    from .Object import ObjectHeader
    from .ProjectPrivilege import ProjectPrivilege
    from .UserPreferences import UserPreferences

# Typings, to be clear that these are not e.g. object IDs
UserIDT = int
UserIDListT = List[int]
GuestIDT = int
GuestIDListT = List[int]


class UserStatus(int, Enum):
    blocked = -1
    inactive = 0
    active = 1
    pending = 2


class UserType(str, Enum):
    guest = "guest"
    user = "user"


NO_ORGANIZATION_ADDED = "Error adding organization name"
OrganizationIDT = int
OrganizationIDListT = List[int]


class PeopleOrganizationDirectory(str, Enum):
    orcid = "https://orcid.org/"
    edmo = "https://edmo.seadatanet.org/"


class Organization(Model):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(
        Integer, Sequence("organizations_id_seq"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(512), unique=True)
    directories: Mapped[str | None] = mapped_column(String(2000))

    def __str__(self):
        return "{0} ({1})".format(self.name, self.directories)


class Person(Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, Sequence("seq_users"), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(50))
    orcid: Mapped[str | None] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(10))
    usercreationdate: Mapped[datetime | None] = mapped_column(TIMESTAMP, default=func.now())
    organization_id: Mapped[int | None] = mapped_column(
        INTEGER, ForeignKey("organizations.id")
    )
    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        organization: Mapped[Organization]
    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": "person",
    }

    @property
    def organisation(self):
        if self.organization is None:
            return ""
        return self.organization.name

    def __str__(self):
        return "{0} ({1})".format(self.name, self.email)


class Guest(Person):
    __mapper_args__ = {
        "polymorphic_identity": "guest",
    }

    def to_user(self) -> "User":
        user = User()
        user.id = self.id
        user.name = self.name
        user.email = self.email
        user.country = self.country
        user.orcid = self.orcid
        user.usercreationdate = self.usercreationdate
        user.organization_id = self.organization_id
        return user


class User(Person):
    password: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[int | None] = mapped_column(SmallInteger(), default=1)
    status_date: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    status_admin_comment: Mapped[str | None] = mapped_column(String(255))
    preferences: Mapped[str | None] = mapped_column(String(40000))
    usercreationreason: Mapped[str | None] = mapped_column(String(1000))
    # Mail status: True for verified, default NULL
    mail_status: Mapped[bool | None] = mapped_column(Boolean())
    # Date the mail status was set
    mail_status_date: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    __mapper_args__ = {
        "polymorphic_identity": "user",
    }

    if TYPE_CHECKING:
        # The relationships are created in Relations.py but the typing here helps the IDE
        roles: Mapped[List["Role"]]
        # The projects that user has rights in, so he/she can participate at various levels.
        privs_on_projects: Mapped[List[ProjectPrivilege]]
        # The objects of which _present_ classification was done by the user
        classified_objects: Mapped[
            List[ObjectHeader]
        ]  # TODO: Repeat should not be needed, mypy bug
        # Preferences, one instance for each project
        preferences_for_projects: Mapped[List[UserPreferences]]

    def has_role(self, role: str) -> bool:
        # TODO: Cache a bit. All roles are just python objects due to SQLAlchemy magic.
        return role in [r.name for r in self.roles]

    def is_manager(self) -> bool:
        return self.has_role(Role.APP_ADMINISTRATOR) or self.has_role(
            Role.USERS_ADMINISTRATOR
        )


class Role(Model):
    """
    The roles granted to users.
    """

    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer(), primary_key=True)  # ,Sequence('seq_roles')
    name: Mapped[str] = mapped_column(String(80), unique=True)

    if TYPE_CHECKING:
        # The relationship(s) are created in Relations.py but the typing here helps IDE
        users: Mapped[List[User]]

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
    user_id: Mapped[int] = mapped_column(
        Integer(), ForeignKey("users.id"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        Integer(), ForeignKey("roles.id"), primary_key=True
    )


class Country(Model):
    """
    TODO: There is no FK from users
    """

    __tablename__ = "countrylist"
    countryname: Mapped[str] = mapped_column(String(50), primary_key=True)


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
    user_id: Mapped[int] = mapped_column(
        Integer(),
        ForeignKey(
            "users.id", name="user_password_reset_user_id_fkey", ondelete="CASCADE"
        ),
        primary_key=True,
    )
    temp_password: Mapped[str] = mapped_column(String(255))
    creation_date: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=func.now()
    )


class UserQuality(Model):
    """
    Store user password quality.
    """

    __tablename__ = "user_quality"
    user_id: Mapped[int] = mapped_column(
        Integer(),
        ForeignKey("users.id", name="user_quality_user_id_fkey", ondelete="CASCADE"),
        primary_key=True,
    )
    password_strong: Mapped[bool] = mapped_column(Boolean())
    check_date: Mapped[datetime] = mapped_column(
        TIMESTAMP, default=func.now(), onupdate=func.now()
    )
