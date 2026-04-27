# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import json
from datetime import datetime
from typing import Dict, List, Any, Set, TextIO

from API_models.filters import ProjectFiltersDict
from BO.Mappings import ProjectMapping
from BO.ObjectSet import DescribedObjectSet
from DB.Acquisition import Acquisition
from DB.Image import Image
from DB.Object import ObjectHeader, ObjectFields
from DB.Process import Process
from DB.Project import Project
from DB.Sample import Sample
from DB.helpers import Result
from DB.helpers.Direct import text
from DB.helpers.ORM import Model, contains_eager, any_
from DB.helpers.SQL import SelectClause
from formats.JSONObjectSet import JSON_FIELDS, JSONDesc
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer
from .Subset import DBObjectTupleT
from .helpers.Service import Service

logger = get_logger(__name__)


class JsonDumper(Service):
    """
    Dump in JSON form a project content, with filters.
        Mapped columns are rendered with their user-visible name (TSV one).
        The fields are reduced to 4(max)-letter names for saving bandwidth and DB fields independence.
    TODO as an option:
        No numeric primary or foreign key is present so the output can be diff-ed.
        The sub-entities are ordered by their 'natural' key, e.g. sample_id for samples.
    """

    def __init__(self, current_user: int, prj_id: int, filters: ProjectFiltersDict):
        super().__init__()
        self.requester_id = current_user
        self.filters = filters
        prj = self.get_session().query(Project).get(prj_id)
        # We don't check for existence, so self.prj is Optional[]
        self.prj = prj
        # Work vars
        self.mapping = ProjectMapping()
        if self.prj:
            self.mapping.load_from_project(self.prj)
        self.already_dumped: Set[Model] = set()
        self.first_query = True

    def run(self, out_stream: TextIO) -> None:
        """
        Produce the json into given stream.
        """
        to_stream: Dict[str, Any]
        if self.prj is None:
            to_stream = {}
        else:
            ids_to_dump = self._find_what_to_dump()  # Filtered IDs
            _to_dump = self._db_fetch(
                ids_to_dump
            )  # Load into SQLA only filtered-in ones
            # prj = to_dump[0][0]
            if len(ids_to_dump) == 0 or len(_to_dump) == 0:
                to_stream = {}
            else:
                to_stream = self.dump_row(out_stream, self.prj)
        json.dump(obj=to_stream, fp=out_stream, indent="  ")

    def dump_row(self, out_stream: TextIO, a_row: Model) -> Dict[str, Any]:
        """
        Dump inside returned value the fields and contained/linked entities from a_row.
        """
        ret: Dict[str, Any] = {}
        self._dump_into_dict(out_stream, a_row, ret)
        return ret

    def _dump_into_dict(
        self, out_stream: TextIO, a_row: Model, tgt_dict: Dict[str, Any]
    ) -> None:
        """
        Dump inside the tgt_dict all fields and contained/linked entities from a_row.
        """
        # Ensure there no infinite loop
        assert a_row not in self.already_dumped
        self.already_dumped.add(a_row)
        # Dump using instructions
        row_class = type(a_row)
        desc: JSONDesc = JSON_FIELDS[row_class]
        for a_field_or_relation, how in desc.items():
            if callable(a_field_or_relation):
                attr = a_field_or_relation(a_row)
            else:
                fld_name = a_field_or_relation.key
                # This is where SQLAlchemy does all its magic when it's a relation
                attr = getattr(a_row, fld_name)  # type:ignore # case2
            if isinstance(attr, list):
                # Serialize the list of child entities, ordinary relationship
                children: List[Dict[str, Any]] = []
                tgt_dict[how] = children

                # Sort to have a stable output
                def dump_sort_key(obj):
                    if hasattr(obj, "objid"):
                        return obj.objid
                    if hasattr(obj, "sampleid"):
                        return obj.sampleid
                    if hasattr(obj, "acquisid"):
                        return obj.acquisid
                    return obj

                for a_child_row in sorted(attr, key=dump_sort_key):
                    child_obj = self.dump_row(out_stream, a_child_row)
                    children.append(child_obj)
            elif isinstance(attr, Model):
                # A twin object AKA 'uselist=False' relationship
                if isinstance(attr, Process):
                    # Keep process in single-entity list for now
                    child_obj = self.dump_row(out_stream, attr)
                    tgt_dict[how] = [child_obj]
                else:
                    # Dump into same output dict.
                    self._dump_into_dict(out_stream, attr, tgt_dict)
            elif isinstance(attr, datetime):
                tgt_dict[how] = attr.isoformat()
            else:
                # Ordinary field
                if attr is not None:
                    tgt_dict[how] = attr
        # Dump mapped fields if any
        tbl_mapping = self.mapping.by_table_name.get(row_class.__tablename__)
        if tbl_mapping is not None:
            for a_db_col, a_tsv_col in tbl_mapping.real_cols_to_tsv.items():
                attr = getattr(a_row, a_db_col)
                if attr is not None:
                    tgt_dict[a_tsv_col] = attr

    def _find_what_to_dump(self) -> List[int]:
        """
        Determine the objects to dump.
        """
        assert self.prj is not None
        # Prepare a where clause and parameters from filter
        if len(self.filters) == 0:
            sql = (
                "SELECT obh.objid"
                "  FROM obj_head obh "
                "  JOIN acquisitions acq ON obh.acquisid = acq.acquisid "
                "  JOIN samples sam ON acq.acq_sample_id = sam.sampleid "
                " WHERE sam.projid = :prj"
            )
            params = {"prj": self.prj.projid}
        else:
            object_set: DescribedObjectSet = DescribedObjectSet(
                self.session, self.prj, self.requester_id, self.filters
            )
            select_clause = SelectClause().add_expr("obh.objid")
            from_, where, params = object_set.get_sql(select_clause)

            sql = select_clause.get_sql() + " FROM " + from_.get_sql() + where.get_sql()

        logger.info("SQL=%s", sql)
        logger.info("SQLParam=%s", params)

        with CodeTimer("Get IDs:", logger):
            res: Result = self.session.execute(text(sql), params)
        ids = [r["objid"] for r in res.mappings()]

        logger.info("NB OBJIDS=%d", len(ids))

        return ids

    def _db_fetch(self, objids: List[int]) -> List[DBObjectTupleT]:
        """
        Do a DB read of given objects, with auxiliary objects.
        Thanks to 'contains_eager' calls, the objects are loaded into SQLAlchemy session.
        :param objids:
        :return:
        """
        ret = self.session.query(
            Project, Sample, Acquisition, Process, ObjectHeader, ObjectFields, Image
        )
        ret = ret.join(Sample, Project.all_samples).options(
            contains_eager(Project.all_samples)
        )
        ret = ret.join(Acquisition, Sample.all_acquisitions)
        ret = ret.join(Process, Acquisition.process)
        ret = ret.join(ObjectHeader, Acquisition.all_objects)
        # Natural joins
        ret = ret.join(ObjectFields)
        ret = ret.join(Image, ObjectHeader.all_images).options(
            contains_eager(ObjectHeader.all_images)
        )
        ret = ret.filter(ObjectHeader.objid == any_(objids))

        if self.first_query:
            logger.info("Query: %s", str(ret))
            self.first_query = False

        with CodeTimer("Get Objects:", logger):
            objs = [an_obj for an_obj in ret]

        # We get as many lines as images
        logger.info("NB ROWS JOIN=%d", len(objs))

        return objs
