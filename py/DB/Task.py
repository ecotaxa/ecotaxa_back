# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from sqlalchemy import Sequence, Column, ForeignKey
from sqlalchemy.dialects.postgresql import VARCHAR, INTEGER, DATE
from sqlalchemy.orm import relationship

from .User import User
from .helpers.ORM import Model


class Task(Model):
    __tablename__ = 'temp_tasks'
    id = Column(INTEGER, Sequence('seq_temp_tasks'), primary_key=True)
    owner_id = Column(INTEGER, ForeignKey('users.id'))
    owner_rel = relationship(User)
    taskclass = Column(VARCHAR(80))
    taskstate = Column(VARCHAR(80))
    taskstep = Column(INTEGER)
    progresspct = Column(INTEGER)
    progressmsg = Column(VARCHAR)
    inputparam = Column(VARCHAR)
    # TODO: Datetime() ?
    creationdate = Column(DATE)
    lastupdate = Column(DATE)

    def __str__(self):
        return "{0} ({1})".format(self.id, self.taskclass)


setattr(Task, "questiondata", Column(VARCHAR))
setattr(Task, "answerdata", Column(VARCHAR))
