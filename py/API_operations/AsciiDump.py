# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from sqlalchemy import Table, text

from DB.Acquisition import Acquisition
from DB.Image import Image
from DB.Object import Object, ObjectFields
from DB.Process import Process
from DB.Project import Project
from DB.Sample import Sample
from DB.helpers.ORM import Model
from .helpers.Service import Service


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
            self.dump_table(fd, Sample, "projid=%d" % projid)
            self.dump_table(fd, Process, "projid=%d" % projid)
            self.dump_table(fd, Acquisition, "projid=%d" % projid)
            self.dump_table(fd, Object, "projid=%d" % projid)
            self.dump_table(fd, ObjectFields, "objfid in (select objid from obj_head where projid=%s)" % projid)
            self.dump_table(fd, Image, "objid in (select objid from obj_head where projid=%s)" % projid)

    def dump_table(self, out, a_table: Model, where):
        base_table: Table = a_table.__table__
        cols = [a_col.name for a_col in base_table.columns]
        pk = [a_pk_col.name for a_pk_col in base_table.primary_key]
        res = self.session.execute(base_table.select().where(text(where)).order_by(pk[0]))
        for a_row in res:
            vals = []
            for col, col_val in zip(cols, a_row):
                if col_val is not None:
                    vals.append("%s=%s" % (col, repr(col_val)))
            ln = "%s(%s)" % (base_table, ",".join(vals))
            print(ln, file=out)
