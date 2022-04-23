# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#

from sqlalchemy import event

from DB.helpers.ORM import Model, Insert
from data.Instruments import DEFAULT_INSTRUMENTS
from .helpers.DDL import Column
from .helpers.Postgres import VARCHAR

InstrumentIDT = str

UNKNOWN_INSTRUMENT = DEFAULT_INSTRUMENTS[-1][0]


class Instrument(Model):
    """
        Reference list of instruments.
    """
    __tablename__ = 'instrument'
    instrument_id: str = Column(VARCHAR(32), primary_key=True)
    name: str = Column(VARCHAR(255))
    bodc_url: str = Column(VARCHAR(255))

    def __str__(self):
        return "{0} ({1})".format(self.instrument_id, self.name)


@event.listens_for(Instrument.__table__, 'after_create')
def insert_initial_instrument_values(_table, sess, **kwargs):
    """
        Create default instruments after table creation.
    """
    for ins_id, ins_name, ins_url in DEFAULT_INSTRUMENTS:
        ins = Insert(Instrument).values((ins_id, ins_name, ins_url))
        sess.execute(ins)
