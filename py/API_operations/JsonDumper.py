# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import IO, Type, Dict

from sqlalchemy import Table, text

from API_models.crud import ProjectFilters
from DB.Project import Project
from DB.helpers.ORM import ModelT, Column
from .helpers.Service import Service


class JsonDumper(Service):
    """
        Dump in JSON form a project content, with filters.
            No numeric primary or foreign key is present so the output can be diff-ed.
            The sub-entities are ordered by their 'natural' key, e.g. sample_id for samples.
            Mapped columns are rendered with their user-visible name (TSV one).
            The fields are reduced to 3-letter names for saving bandwidth and DB fields independance.
    """

    def __init__(self, prj_id: int, filters: ProjectFilters):
        super().__init__()
        self.filters = filters
        prj = self.session.query(Project).get(prj_id)
        assert prj is not None
        self.prj: Project = prj

    JSON_FIELDS: Dict[ModelT, Dict[Column, str]] = \
        {Project: {Project.title: "ttl"}}

    def run(self, out_stream: IO):

        """
            Produce the json into given stream.
        """
        self.dump_table(out_stream, Project, "projid=%d" % self.prj.projid)

        #     self.dump_table(fd, Sample, "projid=%d" % projid)
        #     self.dump_table(fd, Process, "projid=%d" % projid)
        #     self.dump_table(fd, Acquisition, "projid=%d" % projid)
        #     self.dump_table(fd, Object, "projid=%d" % projid)
        #     self.dump_table(fd, ObjectFields, "objfid in (select objid from obj_head where projid=%s)" % projid)
        #     self.dump_table(fd, Image, "objid in (select objid from obj_head where projid=%s)" % projid)
        # return fd

    def dump_table(self, out_stream: IO, a_table: ModelT, where: str):
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
            print(ln, file=out_stream)
