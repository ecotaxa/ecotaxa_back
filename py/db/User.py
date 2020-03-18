# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
import time

from sqlalchemy import Column, ForeignKey, Sequence, Integer, String, Boolean, func
from sqlalchemy.dialects.postgresql import TIMESTAMP

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
        return self.name


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

    def __str__(self):
        return "{0} ({1})".format(self.name, self.email)

    def GetPref(self, prjid, name, defval):
        try:
            prjid = str(prjid)
            tmp = json.loads(self.preferences)
            if prjid not in tmp:
                return defval
            if isinstance(defval, int):
                return int(tmp[prjid].get(name, defval))
            if isinstance(defval, (float)):
                return float(tmp[prjid].get(name, defval))
            return tmp[prjid].get(name, defval)
        except:
            return defval

    def SetPref(self, prjid, name, newval):
        try:
            prjid = str(prjid)
            tmp = json.loads(self.preferences)
            if prjid not in tmp:
                tmp[prjid] = {}
            if tmp[prjid].get(name, -99999) == newval:
                return 0  # déjà la bonne valeur donc il n'y a rien à faire
        except:
            tmp = {}
        if prjid not in tmp:
            tmp[prjid] = {}
        tmp[prjid][name] = newval
        tmp[prjid]['ts'] = time.time()
        if len(tmp) > 75:  # si des settings pour plus de 50 projets on ne garde que les 25 plus recents
            newpref = {k: v for k, v in tmp.items() if isinstance(v, dict) and 'ts' in v}
            ChronoSorted = [[k, v['ts']] for k, v in newpref.items()]
            sorted(ChronoSorted, key=lambda r: r[1], reverse=True)
            tmp = {}
            for id, ts in ChronoSorted[0:50]:
                tmp[id] = newpref[id]
        self.preferences = json.dumps(tmp)
        return 1
