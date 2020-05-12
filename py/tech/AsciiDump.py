# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from sqlalchemy import Table, text

from db.Acquisition import Acquisition
from db.Image import Image
from db.Model import Model
from db.Object import Object, ObjectFields
from db.Process import Process
from db.Project import Project
from db.Sample import Sample
from framework.Service import Service


class AsciiDumper(Service):
    """
        A utility service for having a predictable and diff-able dump of the DB.
        Reason: Postgres does not do "order by" on ascii dumps so it's a bit tricky to intepret
        differences.
    """

    def __init__(self):
        super().__init__()

    # noinspection PyTypeChecker
    def run(self, projid: int, out: str):
        """
            Produce the file.
        """
        with open(out, "w") as fd:
            self.dump_table(fd, Project, "projid=%d" % projid)
            self.dump_table(fd, Object, "projid=%d" % projid)
            self.dump_table(fd, ObjectFields, "objfid in (select objid from obj_head where projid=%s)" % projid)
            self.dump_table(fd, Image, "objid in (select objid from obj_head where projid=%s)" % projid)
            self.dump_table(fd, Process, "projid=%d" % projid)
            self.dump_table(fd, Sample, "projid=%d" % projid)
            self.dump_table(fd, Acquisition, "projid=%d" % projid)

    def dump_table(self, out, a_table: Model, where):
        base_table: Table = a_table.__table__
        cols = [a_col.name for a_col in base_table.columns]
        pk = [a_pk_col.name for a_pk_col in base_table.primary_key]
        res = self.session.execute(base_table.select().where(text(where)).order_by(pk[0]))
        for a_row in res:
            row_dict = dict(zip(cols, a_row))
            print(repr(row_dict), file=out)
