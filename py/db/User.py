# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List

from sqlalchemy import Column, ForeignKey, Sequence, Integer, String, Boolean, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
# noinspection PyProtectedMember
from sqlalchemy.engine import ResultProxy
from sqlalchemy.orm import Session

from utils import none_to_empty
from .Model import Model


class UserRole(Model):
    __tablename__ = 'users_roles'
    user_id = Column(Integer(), ForeignKey('User.id'), primary_key=True)
    role_id = Column(Integer(), ForeignKey('Role.id'), primary_key=True)


class Role(Model):  # TODO, RoleMixin):
    __tablename__ = 'roles'
    id = Column(Integer(), primary_key=True)  # ,Sequence('seq_roles')
    name = Column(String(80), unique=True, nullable=False)

    #    description = Column(String(255))
    def __str__(self):
        return "{0} ({1})".format(self.name, self.id)


class User(Model):  # TODO , UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('seq_users'), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255))
    name = Column(String(255), nullable=False)
    organisation = Column(String(255))
    active = Column(Boolean(), default=True)
    # TODO roles = relationship('Role', secondary=UserRole,
    #                         backref=backref('users', lazy='dynamic'))  #
    preferences = Column(String(40000))
    country = Column(String(50))
    usercreationdate = Column(TIMESTAMP, default=func.now())
    usercreationreason = Column(String(1000))

    @staticmethod
    def find_users(session: Session, names: List[str], emails: List[str], found_users: dict):
        """
            Find the users in DB, by name or email.
        """
        res: ResultProxy = session.execute(
            "SELECT id, lower(name), lower(email) "
            "  FROM users "
            " WHERE lower(name) = ANY(:nms) or email = ANY(:ems) ",
            {"nms": names, "ems": emails})
        for rec in res:
            for u in found_users:
                if u == rec[1] or none_to_empty(found_users[u].get('email')).lower() == rec[2]:
                    found_users[u]['id'] = rec[0]

    def __str__(self):
        return "{0} ({1})".format(self.name, self.email)
