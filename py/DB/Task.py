# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from .helpers.DDL import Sequence, Column, ForeignKey
from .helpers.ORM import Model
from .helpers.ORM import relationship
from .helpers.Postgres import VARCHAR, INTEGER, DATE


class Task(Model):
    __tablename__ = 'temp_tasks'
    id = Column(INTEGER, Sequence('seq_temp_tasks'), primary_key=True)
    owner_id = Column(INTEGER, ForeignKey('users.id'))
    taskclass = Column(VARCHAR(80))
    taskstate = Column(VARCHAR(80))
    taskstep = Column(INTEGER)
    progresspct = Column(INTEGER)
    progressmsg = Column(VARCHAR)
    inputparam = Column(VARCHAR)
    # TODO: Datetime() ?
    creationdate = Column(DATE)
    lastupdate = Column(DATE)

    # The relationships are created in Relations.py but the typing here helps the IDE
    owner: relationship

    def __str__(self):
        return "{0} ({1})".format(self.id, self.taskclass)


setattr(Task, "questiondata", Column(VARCHAR))
setattr(Task, "answerdata", Column(VARCHAR))
