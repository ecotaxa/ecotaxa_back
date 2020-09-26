# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A set of Object as seen by the user, e.g. on classification page.
#
# The set comprises all objects from a Project, except the ones filtered by a set of criteria.
#
from typing import Tuple, Optional, List, Iterator, Callable

from sqlalchemy import select, text, func

from API_models.crud import ProjectFilters, ColUpdateList
from BO.Classification import HistoricalClassif
from BO.Project import ProjectIDListT
from BO.Taxonomy import TaxonomyBO
from BO.helpers.MappedTable import MappedTable
from DB import Project, ObjectHeader, Image, and_
from DB.Object import ObjectsClassifHisto, ObjectFields
from DB.helpers.ORM import Session, Query, Delete, Update, Insert, any_, postgresql, or_, case, not_
from DB.helpers.SQL import WhereClause, SQLParamDict
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

# Typings, to be clear that these are not e.g. project IDs
ObjectIDListT = List[int]
# Object_id + parents
ObjectIDWithParentsListT = List[Tuple[int, int, int, int]]

logger = get_logger(__name__)


class DescribedObjectSet(object):
    """
        A (potentially large) set of objects, described by a base rule (all objects in project XXX)
        and filtered by exclusion conditions.
    """

    def __init__(self, session: Session, prj_id: int, filters: ProjectFilters):
        self.prj_id = prj_id
        self.filters = ObjectSetFilter(session, filters)

    def get_sql(self, user_id: int) -> Tuple[WhereClause, SQLParamDict]:
        """
            Construct SQL parts for getting the IDs of objects.
            :return:
        """
        where = WhereClause()
        where *= " oh.projid = :projid "
        params: SQLParamDict = {"projid": self.prj_id}
        self.filters.get_sql_filter(where, params, user_id)
        return where, params


class EnumeratedObjectSet(MappedTable):
    """
        A set of objects, described by all their IDs.
    """

    def __init__(self, session: Session, object_ids: ObjectIDListT):
        super().__init__(session)
        self.object_ids = object_ids

    def __len__(self):
        return len(self.object_ids)

    def get_objectid_chunks(self, chunk_size: int) -> Iterator[ObjectIDListT]:
        """
            Yield successive n-sized chunks from l.
            Adapted from
            https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks/312464#312464
        """
        lst = self.object_ids
        for idx in range(0, len(lst), chunk_size):
            yield lst[idx:idx + chunk_size]

    def get_projects_ids(self) -> ProjectIDListT:
        """
            Return the project IDs for the owned objectsIDs.
        """
        qry: Query = self.session.query(Project.projid).distinct(Project.projid)
        qry = qry.join(Project.all_objects)
        qry = qry.filter(ObjectHeader.objid == any_(self.object_ids))
        with CodeTimer("Prjs for %d objs: " % len(self.object_ids), logger):
            return [an_id[0] for an_id in qry.all()]

    @staticmethod
    def _delete_chunk(session: Session, a_chunk: ObjectIDListT) -> Tuple[int, int, List[str]]:
        """
            Delete a chunk from self's object list.
            Technical Note: We use SQLA Core as we don't want to fetch the rows
        """
        # Start with images which are not deleted via a CASCADE on DB side
        # This is maybe due to relationship cycle b/w ObjectHeader and Images @See comment in Image class
        img_del_qry: Delete = Image.__table__.delete()
        img_del_qry = img_del_qry.where(Image.objid == any_(a_chunk))
        img_del_qry = img_del_qry.returning(Image.file_name, Image.thumb_file_name)
        with CodeTimer("DELETE for %d images: " % len(a_chunk), logger):
            files_res = session.execute(img_del_qry)
            img_files = []
            nb_img_rows = 0
            for a_file_tuple in files_res:
                # We have main file and optionally the thumbnail one
                for a_file in a_file_tuple:
                    if a_file:
                        img_files.append(a_file)
                nb_img_rows += 1
            logger.info("Removed: %d rows, to remove: %d files", nb_img_rows, len(img_files))

        obj_del_qry: Delete = ObjectHeader.__table__.delete()
        obj_del_qry = obj_del_qry.where(ObjectHeader.objid == any_(a_chunk))
        with CodeTimer("DELETE for %d objs: " % len(a_chunk), logger):
            nb_objs = session.execute(obj_del_qry).rowcount

        session.commit()
        return nb_objs, nb_img_rows, img_files

    def delete(self, chunk_size: int, do_with_files: Optional[Callable[[List[str]], None]]) -> \
            Tuple[int, int, List[str]]:
        """
            Delete all objects in this set, in 'small' DB transactions.
        """
        nb_objs, nb_img_rows, img_files = 0, 0, []
        # Pick chunks of object ids
        for a_chunk in self.get_objectid_chunks(chunk_size):
            # Delete them
            o, r, i = self._delete_chunk(self.session, a_chunk)
            # Cumulate stats
            nb_objs += o
            nb_img_rows += r
            if do_with_files:
                do_with_files(i)
            img_files.extend(i)

        return nb_objs, nb_img_rows, img_files

    def reset_to_predicted(self):
        """
            Reset to Predicted state, keeping log, i.e. history, of previous change.
        """
        oh = ObjectHeader
        self.historize_classification(oh, ['V', 'D'])

        # Update objects table
        obj_upd_qry: Update = oh.__table__.update()
        obj_upd_qry = obj_upd_qry.where(and_(oh.objid == any_(self.object_ids),
                                             (oh.classif_qual.in_(['V', 'D']))))
        obj_upd_qry = obj_upd_qry.values(classif_qual='P')
        nb_objs = self.session.execute(obj_upd_qry).rowcount
        logger.info(" %d out of %d rows reset to predicted", nb_objs, len(self.object_ids))

        self.session.commit()

    def historize_classification(self, oh, only_qual):
        """
           Copy current classification information into history table, for all rows in self.
        """
        # Light up a bit the SQLA expressions
        och = ObjectsClassifHisto
        # What we want to historize, as a subquery
        sel_subqry = select([oh.objid, oh.classif_when, text("'M'"), oh.classif_id,
                             oh.classif_qual, oh.classif_who])
        sel_subqry = sel_subqry.where(and_(oh.objid == any_(self.object_ids),
                                           (oh.classif_qual.in_(only_qual)),
                                           (oh.classif_when is not None)
                                           )
                                      )
        # Insert into the log table
        from sqlalchemy.dialects.postgresql import insert
        ins_qry: Insert = insert(och.__table__)
        ins_qry = ins_qry.from_select([och.objid, och.classif_date, och.classif_type, och.classif_id,
                                       och.classif_qual, och.classif_who], sel_subqry)
        ins_qry = ins_qry.on_conflict_do_nothing(constraint='objectsclassifhisto_pkey')
        logger.info("Histo query: %s", ins_qry.compile(dialect=postgresql.dialect()))
        nb_objs = self.session.execute(ins_qry).rowcount
        logger.info(" %d out of %d rows copied to log", nb_objs, len(self.object_ids))
        return oh

    def apply_on_all(self, project: Project, updates: ColUpdateList) -> int:
        """
            Apply all updates on all objects pointed at by the list.
            Depending on the field it becomes an object_header or an object_fields update.
        """
        upd0 = updates[0]
        if upd0["ucol"] in ObjectHeader.__dict__:
            if upd0["ucol"] == "classif_id":
                self.historize_classification(ObjectHeader, ['V', 'D', 'P', None])
            return self._apply_on_all_non_mapped(ObjectHeader, updates)
        else:
            return self._apply_on_all(ObjectFields, project, updates)

    def add_filter(self, upd):
        if "obj_head." in str(upd):
            ret = upd.filter(ObjectHeader.objid == any_(self.object_ids))
        else:
            ret = upd.filter(ObjectFields.objfid == any_(self.object_ids))
        return ret

    def _get_last_classif_history(self, from_user_id: Optional[int], but_not_from_user_id: Optional[int]) \
            -> List[HistoricalClassif]:
        """
            Query for classification history on all objects of self.
        """
        # Get the histo entries
        subqry = self.session.query(ObjectsClassifHisto,
                                    func.rank().over(partition_by=ObjectsClassifHisto.objid,
                                                     order_by=ObjectsClassifHisto.classif_date.desc()).
                                    label("rnk"))
        if from_user_id:
            subqry = subqry.filter(ObjectsClassifHisto.classif_who == from_user_id)
        if but_not_from_user_id:
            subqry = subqry.filter(ObjectsClassifHisto.classif_who != but_not_from_user_id)
        subqry = subqry.filter(ObjectsClassifHisto.classif_type == "M")
        subqry = subqry.filter(ObjectsClassifHisto.objid == any_(self.object_ids)).subquery()

        # Also get some fields from ObjectHeader for referencing, info, and fallback
        qry = self.session.query(ObjectHeader.objid, ObjectHeader.classif_id,
                                 func.coalesce(subqry.c.classif_date, ObjectHeader.classif_auto_when),
                                 subqry.c.classif_type,
                                 func.coalesce(subqry.c.classif_id, ObjectHeader.classif_auto_id).label("h_classif_id"),
                                 func.coalesce(subqry.c.classif_qual,
                                               case([(not_(ObjectHeader.classif_auto_id.is_(None)), 'P')])),
                                 subqry.c.classif_who)
        qry = qry.join(subqry, ObjectHeader.objid == subqry.c.objid, isouter=(from_user_id is None))
        if from_user_id is not None:
            # If taking history from a user, don't apply to the objects he/she classsified
            # in last already.
            qry = qry.filter(ObjectHeader.classif_who != from_user_id)
            qry = qry.filter(subqry.c.rnk == 1)
        else:
            # Taking any history, including nothing, so emit blank history (see isouter above)
            qry = qry.filter(ObjectHeader.objid == any_(self.object_ids))
            qry = qry.filter(or_(subqry.c.rnk == 1, subqry.c.rnk.is_(None)))
        logger.info("_get_last_classif_history qry:%s", str(qry))
        with CodeTimer("HISTORY for %d objs: " % len(self.object_ids), logger):
            ret = [HistoricalClassif(rec) for rec in qry.all()]
        logger.info("_get_last_classif_history qry: %d rows", len(ret))
        return ret

    def revert_to_history(self, from_user_id: Optional[int], but_not_from_user_id: Optional[int]) \
            -> List[HistoricalClassif]:
        """
            Update self's objects so that current classification becomes the last one from hist_user_id,
        :param from_user_id: If set (!= None), the user_id to copy classification from. If unset then pick any recent.
        :param but_not_from_user_id: If set (!= None), exclude this user from history picking.
        """
        histo = self._get_last_classif_history(from_user_id, but_not_from_user_id)
        # Bulk update. It's less efficient than a plain update with criteria, but in the future we
        # might be able to do some cherry picking on the history.
        updates = [{ObjectHeader.objid.name: an_histo.objid,
                    ObjectHeader.classif_id.name: an_histo.histo_classif_id,
                    ObjectHeader.classif_who.name: an_histo.histo_classif_who,
                    ObjectHeader.classif_when.name: an_histo.histo_classif_date,
                    ObjectHeader.classif_qual.name: an_histo.histo_classif_qual}
                   for an_histo in histo]
        self.session.bulk_update_mappings(ObjectHeader, updates)
        self.session.commit()
        return histo

    def evaluate_revert_to_history(self, from_user_id: Optional[int], but_not_from_user_id: Optional[int]) \
            -> List[HistoricalClassif]:
        """
            Same as @see revert_to_history but don't commit the changes, just return them.
        """
        histo = self._get_last_classif_history(from_user_id, but_not_from_user_id)
        return histo


class ObjectSetFilter(object):
    """
        A filter for reducing an object set.
    """

    def __init__(self, session: Session, filters: ProjectFilters):
        """
            Init from a dictionary with all fields.
        """
        self.session = session
        # Now to the filters
        self.taxo: Optional[str] = filters.get("taxo", "")
        self.taxo_child: bool = filters.get("taxochild", "") == "Y"
        self.statusfilter: Optional[str] = filters.get("statusfilter", "")
        self.MapN: Optional[str] = filters.get("MapN", '')
        self.MapW: Optional[str] = filters.get("MapW", '')
        self.MapE: Optional[str] = filters.get("MapE", '')
        self.MapS: Optional[str] = filters.get("MapS", '')
        self.depth_min: Optional[str] = filters.get("depthmin", '')
        self.depth_max: Optional[str] = filters.get("depthmax", '')
        # A coma-separated list of numerical sample ids
        self.samples: Optional[str] = filters.get("samples", '')
        self.instrument: Optional[str] = filters.get("instrum", '')
        # A coma-separated list of sunpos values
        #  D for Day, U for Dusk, N for Night, A for Dawn (Aube in French)
        self.daytime: Optional[str] = filters.get("daytime", "")
        # A coma-separated list of month numbers
        self.months: Optional[str] = filters.get("month", "")
        self.from_date: Optional[str] = filters.get("fromdate", '')
        self.to_date: Optional[str] = filters.get("todate", '')
        # Time (in day) filters
        self.from_time: Optional[str] = filters.get("fromtime", '')
        self.to_time: Optional[str] = filters.get("totime", '')
        self.invert_time: bool = filters.get("inverttime", '') == "1"
        # Validation date filters
        self.validated_from: Optional[str] = filters.get("validfromdate", '')
        self.validated_to: Optional[str] = filters.get("validtodate", '')
        # Free fields AKA features filtering
        self.free_num: Optional[str] = filters.get("freenum", '')
        self.free_num_start: Optional[str] = filters.get("freenumst", '')
        self.free_num_end: Optional[str] = filters.get("freenumend", '')
        # Free text filtering
        self.free_text: Optional[str] = filters.get("freetxt", '')
        self.free_text_val: Optional[str] = filters.get("freetxtval", "")
        # A coma-separated list of numerical user ids
        self.annotators: Optional[str] = filters.get('filt_annot', '')
        # Only the last annotator, unlike "filt_annot" which digs in history
        self.last_annotators: Optional[str] = filters.get('filt_last_annot', '')

    def get_sql_filter(self, where_clause: WhereClause,
                       params: SQLParamDict, user_id: int) -> None:
        """
            The generated SQL assumes that, in the query, 'oh' is the alias for object_head aka ObjectHeader
            and 'of' the alias for ObjectFields
        :param user_id: For filtering validators.
        :param where_clause: SQL filtering clauses will be added there.
        :param params: SQL params will be added there.
        :return:
        """

        if self.taxo:
            where_clause *= " oh.classif_id = any (:taxo) "
            if self.taxo_child:
                # TODO: Cache if used
                params['taxo'] = list(TaxonomyBO.children_of(self.session, [int(self.taxo)]))
            else:
                params['taxo'] = [int(x) for x in self.taxo.split(',')]

        if self.statusfilter:
            if self.statusfilter == "NV":
                where_clause *= " (oh.classif_qual != 'V' or oh.classif_qual is null) "
            elif self.statusfilter == "PV":
                where_clause *= " oh.classif_qual in ('V','P') "
            elif self.statusfilter == "NVM":
                where_clause *= " oh.classif_qual = 'V' "
                where_clause *= " oh.classif_who != " + str(user_id) + " "
            elif self.statusfilter == "VM":
                where_clause *= " oh.classif_qual= 'V' "
                where_clause *= " oh.classif_who = " + str(user_id) + " "
            elif self.statusfilter == "U":
                where_clause *= " oh.classif_qual is null "
            else:
                where_clause *= " oh.classif_qual = '" + self.statusfilter + "' "

        if self.MapN and self.MapW and self.MapE and self.MapS:
            where_clause *= " oh.latitude between :MapS and :MapN "
            where_clause *= " oh.longitude between :MapW and :MapE "
            params['MapN'] = self.MapN
            params['MapW'] = self.MapW
            params['MapE'] = self.MapE
            params['MapS'] = self.MapS

        if self.depth_min and self.depth_max:
            where_clause *= " oh.depth_min between :depthmin and :depthmax "
            where_clause *= " oh.depth_max between :depthmin and :depthmax "
            params['depthmin'] = self.depth_min
            params['depthmax'] = self.depth_max

        if self.samples:
            where_clause *= " oh.sampleid = any (:samples) "
            params['samples'] = [int(x) for x in self.samples.split(',')]

        if self.instrument:
            where_clause *= " oh.acquisid in (select acquisid " \
                            "                  from acquisitions " \
                            "                 where instrument ilike :instrum " \
                            "                   and projid = :projid ) "
            params['instrum'] = '%' + self.instrument + '%'

        if self.daytime:
            where_clause *= " oh.sunpos = any (:daytime) "
            params['daytime'] = [x for x in self.daytime.split(',')]

        if self.months:
            where_clause *= " extract(month from oh.objdate) = any (:month) "
            params['month'] = [int(x) for x in self.months.split(',')]

        if self.from_date:
            where_clause *= " oh.objdate >= to_date(:fromdate,'YYYY-MM-DD') "
            params['fromdate'] = self.from_date

        if self.to_date:
            where_clause *= " oh.objdate <= to_date(:todate,'YYYY-MM-DD') "
            params['todate'] = self.to_date

        if self.invert_time:
            if self.from_time and self.to_time:
                where_clause *= " (oh.objtime <= time :fromtime or oh.objtime >= time :totime) "
                params['fromtime'] = self.from_time
                params['totime'] = self.to_time
        else:
            if self.from_time:
                where_clause *= " oh.objtime >= time :fromtime "
                params['fromtime'] = self.from_time
            if self.to_time:
                where_clause *= " oh.objtime <= time :totime "
                params['totime'] = self.to_time

        if self.validated_from:
            where_clause *= " oh.classif_when >= to_timestamp(:validfromdate,'YYYY-MM-DD HH24:MI') "
            params['validfromdate'] = self.validated_from

        if self.validated_to:
            where_clause *= " oh.classif_when <= to_timestamp(:validtodate,'YYYY-MM-DD HH24:MI') "
            params['validtodate'] = self.validated_to

        if self.free_num and self.free_num_start:
            criteria_col = "n%02d" % int(self.free_num[2:])
            where_clause *= " of." + criteria_col + " >= :freenumst "
            params['freenumst'] = self.free_num_start

        if self.free_num and self.free_num_end:
            criteria_col = "n%02d" % int(self.free_num[2:])
            where_clause *= " of." + criteria_col + " <= :freenumend "
            params['freenumend'] = self.free_num_end

        if self.free_text and self.free_text_val:
            criteria_tbl = self.free_text[0]
            criteria_col = "t%02d" % int(self.free_text[2:])
            if criteria_tbl == 'o':
                where_clause *= " of." + criteria_col + " ilike :freetxtval "
            elif criteria_tbl == 'a':
                where_clause *= " oh.acquisid in (select acquisid from acquisitions s " \
                                "                  where " + criteria_col + " ilike :freetxtval " + \
                                "                    and projid = :projid ) "
            elif criteria_tbl == 's':
                where_clause *= " oh.sampleid in (select sampleid from samples s " \
                                "                  where " + criteria_col + " ilike :freetxtval " + \
                                "                    and projid = :projid ) "
            elif criteria_tbl == 'p':
                where_clause *= " oh.processid in (select processid from process s " \
                                "                   where " + criteria_col + " ilike :freetxtval " + \
                                "                     and projid = :projid ) "
            params['freetxtval'] = '%' + self.free_text_val + '%'

        if self.annotators:
            where_clause *= " (oh.classif_who = any (:filt_annot) " \
                            "  or exists (select classif_who " \
                            "               from " + ObjectsClassifHisto.__tablename__ + " och " + \
                            "              where och.objid = oh.objid " \
                            "                and classif_who = any (:filt_annot) ) ) "
            params['filt_annot'] = [int(x) for x in self.annotators.split(',')]
        elif self.last_annotators:
            where_clause *= " oh.classif_who = any (:filt_annot) "
            params['filt_annot'] = [int(x) for x in self.last_annotators.split(',')]
