# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A set of Object as seen by the user, e.g. on classification page.
#
# The set comprises all objects from a Project, except the ones filtered by a set of criteria.
#
from collections import OrderedDict
from decimal import Decimal
from typing import Tuple, Optional, List, Iterator, Callable, Dict, Any

# A Postgresl insert generator, needed for the key conflict clause
from sqlalchemy import bindparam
from sqlalchemy.sql import Alias

from API_models.crud import ProjectFilters
from BO.Classification import HistoricalLastClassif, ClassifIDListT, ClassifIDT
from BO.ColumnUpdate import ColUpdateList
from BO.Object import ObjectIDT, ObjectIDWithParentsT
from BO.Taxonomy import TaxonomyBO
from BO.User import UserIDT
from BO.helpers.MappedTable import MappedTable
from DB import Project, ObjectHeader, Image, Sample, Acquisition
from DB.Object import ObjectsClassifHisto, ObjectFields, PREDICTED_CLASSIF_QUAL, VALIDATED_CLASSIF_QUAL, \
    DUBIOUS_CLASSIF_QUAL
from DB.Project import ProjectIDListT
from DB.helpers import Result, Session
from DB.helpers.Core import select
from DB.helpers.Direct import text, func, true
from DB.helpers.ORM import Query, Delete, Update, Insert, any_, and_, or_, case
from DB.helpers.Postgres import pg_insert
from DB.helpers.SQL import WhereClause, SQLParamDict, FromClause, OrderClause
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

# Typings, to be clear that these are not e.g. project IDs
ObjectIDListT = List[int]
# Object_id + parents + project
ObjectIDWithParentsListT = List[ObjectIDWithParentsT]

logger = get_logger(__name__)


class DescribedObjectSet(object):
    """
        A (potentially large) set of objects, described by a base rule (all objects in project XXX)
        and filtered by exclusion conditions.
    """

    def __init__(self, session: Session, prj_id: int, filters: ProjectFilters):
        self.prj_id = prj_id
        self.filters = ObjectSetFilter(session, filters)

    def get_sql(self, user_id: int,
                order_clause: Optional[OrderClause] = None,
                select_list: str = "",
                all_images: bool = False) \
            -> Tuple[FromClause, WhereClause, SQLParamDict]:
        """
            Construct SQL parts for getting the IDs of objects.
            :param all_images: If not set (default), only return the lowest rank, i.e. visible, image
            :return:
        """
        if order_clause is None:
            order_clause = OrderClause()
        # The filters on objects
        obj_where = WhereClause()
        params: SQLParamDict = {"projid": self.prj_id}
        self.filters.get_sql_filter(obj_where, params, user_id)
        selected_tables = FromClause("obj_head obh")
        selected_tables += "acquisitions acq ON acq.acquisid = obh.acquisid"
        selected_tables += "samples sam ON sam.sampleid = acq.acq_sample_id AND sam.projid = :projid"
        column_referencing_sql = obj_where.get_sql() + order_clause.get_sql() + select_list
        if "prc." in column_referencing_sql:
            selected_tables += "process prc ON prc.processid = acq.acquisid"
        if "obf." in column_referencing_sql:
            selected_tables += "obj_field obf ON obf.objfid = obh.objid"
        if "txo." in column_referencing_sql or "txp." in column_referencing_sql:
            selected_tables += "taxonomy txo ON txo.id = obh.classif_id"
            selected_tables.set_outer("taxonomy txo ")
        if "img." in column_referencing_sql:
            selected_tables += "images img ON obh.objid = img.objid " + \
                               ("AND img.imgrank = (SELECT MIN(img3.imgrank) "
                                "FROM images img3 WHERE img3.objid = obh.objid)" if not all_images else "")
            selected_tables.set_outer("images img ")
        if "usr." in column_referencing_sql:
            selected_tables += "users usr ON obh.classif_who = usr.id"
            selected_tables.set_outer("users usr ")
        if "txp." in column_referencing_sql:
            selected_tables += "taxonomy txp ON txp.id = txo.parent_id"
            selected_tables.set_outer("taxonomy txp ")
        return selected_tables, obj_where, params


class EnumeratedObjectSet(MappedTable):
    """
        A set of objects, described by all their IDs.
    """

    def __init__(self, session: Session, object_ids: ObjectIDListT):
        super().__init__(session)
        assert isinstance(object_ids, list)
        assert len(object_ids) == 0 or isinstance(object_ids[0], ObjectIDT)
        self.object_ids = object_ids

    def add_object(self, object_id: ObjectIDT):
        self.object_ids.append(object_id)

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
        qry = qry.join(Sample)
        qry = qry.join(Acquisition)
        qry = qry.join(ObjectHeader)
        qry = qry.filter(ObjectHeader.objid == any_(self.object_ids))
        with CodeTimer("Prjs for %d objs: " % len(self.object_ids), logger):
            return [an_id for an_id, in qry.all()]

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
        # TODO: Cache delete
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
        self.historize_classification(only_qual=[VALIDATED_CLASSIF_QUAL, DUBIOUS_CLASSIF_QUAL], manual=True)

        # Update objects table
        obj_upd_qry: Update = oh.__table__.update()
        obj_upd_qry = obj_upd_qry.where(and_(oh.objid == any_(self.object_ids),
                                             (oh.classif_qual.in_([VALIDATED_CLASSIF_QUAL, DUBIOUS_CLASSIF_QUAL]))))
        obj_upd_qry = obj_upd_qry.values(classif_qual=PREDICTED_CLASSIF_QUAL)
        nb_objs = self.session.execute(obj_upd_qry).rowcount
        # TODO: Cache upd
        logger.info(" %d out of %d rows reset to predicted", nb_objs, len(self.object_ids))

        self.session.commit()

    def update_all(self, params: Dict) -> int:
        """
            Update all self's objects using given parameters, dict of column names and values.
        """
        # Update objects table
        obj_upd_qry: Update = ObjectHeader.__table__.update()
        obj_upd_qry = obj_upd_qry.where(ObjectHeader.objid == any_(self.object_ids))
        obj_upd_qry = obj_upd_qry.values(params)
        updated_objs = self.session.execute(obj_upd_qry).rowcount
        # TODO: Cache upd
        # prj_id = self.get_projects_ids()[0]
        # ObjectCacheUpdater(prj_id).update_objects(self.object_ids, params)
        return updated_objs

    def historize_classification(self, only_qual, manual):
        """
           Copy current classification information into history table, for all rows in self.
           :param only_qual: If set, only historize for current rows with this classification.
           :param manual: If set, historize manual entries, otherwise, pick automatic ones.
        """
        # Light up a bit the SQLA expressions
        oh = ObjectHeader
        och = ObjectsClassifHisto
        # What's inserted, both cases, into the history table
        ins_columns = [och.objid, och.classif_date, och.classif_type, och.classif_id,
                       och.classif_qual]
        if manual:
            # What we want to historize, as a subquery - The current manual state
            sel_subqry = select([oh.objid, oh.classif_when, text("'M'"), oh.classif_id,
                                 oh.classif_qual, oh.classif_who])
            if only_qual is not None:
                qual_cond = oh.classif_qual.in_(only_qual)
            else:
                qual_cond = true()
            sel_subqry = sel_subqry.where(and_(oh.objid == any_(self.object_ids),
                                               oh.classif_when.isnot(None),
                                               qual_cond
                                               )
                                          )
            ins_columns.append(och.classif_who)  # We can insert 'who did it' as well
        else:
            # What we want to historize, as a subquery
            sel_subqry = select([oh.objid, oh.classif_auto_when, text("'A'"), oh.classif_auto_id,
                                 oh.classif_qual, oh.classif_auto_score])
            sel_subqry = sel_subqry.where(and_(oh.objid == any_(self.object_ids),
                                               oh.classif_auto_id.isnot(None),
                                               oh.classif_auto_when.isnot(None)
                                               )
                                          )
            ins_columns.append(och.classif_score)  # We can insert prediction score as well
        # Insert into the log table
        ins_qry: Insert = pg_insert(och.__table__)
        ins_qry = ins_qry.from_select(ins_columns, sel_subqry)
        ins_qry = ins_qry.on_conflict_do_nothing(constraint='objectsclassifhisto_pkey')
        # TODO: mypy crashes due to pg_dialect below
        # logger.info("Histo query: %s", ins_qry.compile(dialect=pg_dialect()))
        nb_objs = self.session.execute(ins_qry).rowcount
        logger.info(" %d out of %d rows copied to log", nb_objs, len(self.object_ids))
        return oh

    def apply_on_all(self, project: Project, updates: ColUpdateList) -> int:
        """
            Apply all updates on all objects pointed at by the list.
        """
        mapped_updates = []
        direct_updates = []
        for an_upd in updates:
            if an_upd["ucol"] in ObjectHeader.__dict__:
                if an_upd["ucol"] == "classif_id":
                    self.historize_classification(only_qual=None, manual=True)
                direct_updates.append(an_upd)
            else:
                mapped_updates.append(an_upd)
        # Return
        return max(self._apply_on_all_non_mapped(ObjectHeader, direct_updates),
                   self._apply_on_all(ObjectFields, project, mapped_updates))

    def add_filter(self, upd):
        if "obj_head." in str(upd):
            ret = upd.filter(ObjectHeader.objid == any_(self.object_ids))
        else:
            ret = upd.filter(ObjectFields.objfid == any_(self.object_ids))
        return ret

    def _get_last_classif_history(self, from_user_id: Optional[int], but_not_from_user_id: Optional[int]) \
            -> List[HistoricalLastClassif]:
        """
            Query for last classification history on all objects of self, mixed with present state in order
            to have restore-able lines.
        """
        # Get the histo entries
        subqry: Query = self.session.query(ObjectsClassifHisto,
                                           func.rank().over(partition_by=ObjectsClassifHisto.objid,
                                                            order_by=ObjectsClassifHisto.classif_date.desc()).
                                           label("rnk"))
        if from_user_id:
            subqry = subqry.filter(ObjectsClassifHisto.classif_who == from_user_id)
        if but_not_from_user_id:
            subqry = subqry.filter(ObjectsClassifHisto.classif_who != but_not_from_user_id)
        subqry = subqry.filter(ObjectsClassifHisto.classif_type == "M")
        subq_alias: Alias = subqry.filter(ObjectsClassifHisto.objid == any_(self.object_ids)).subquery()

        # Also get some fields from ObjectHeader for referencing, info, and fallback
        qry = self.session.query(ObjectHeader.objid, ObjectHeader.classif_id,
                                 func.coalesce(subq_alias.c.classif_date, ObjectHeader.classif_auto_when),
                                 subq_alias.c.classif_type,
                                 func.coalesce(subq_alias.c.classif_id, ObjectHeader.classif_auto_id).label(
                                     "h_classif_id"),
                                 func.coalesce(subq_alias.c.classif_qual,
                                               case([(ObjectHeader.classif_auto_id.isnot(None), PREDICTED_CLASSIF_QUAL)])),
                                 subq_alias.c.classif_who)
        qry = qry.join(subq_alias, ObjectHeader.objid == subq_alias.c.objid, isouter=(from_user_id is None))
        if from_user_id is not None:
            # If taking history from a user, don't apply to the objects he/she classsified
            # in last already.
            qry = qry.filter(ObjectHeader.classif_who != from_user_id)
            qry = qry.filter(subq_alias.c.rnk == 1)
        else:
            # Taking any history, including nothing, so emit blank history (see isouter above)
            qry = qry.filter(ObjectHeader.objid == any_(self.object_ids))
            qry = qry.filter(or_(subq_alias.c.rnk == 1, subq_alias.c.rnk.is_(None)))
        logger.info("_get_last_classif_history qry:%s", str(qry))
        with CodeTimer("HISTORY for %d objs: " % len(self.object_ids), logger):
            ret = [HistoricalLastClassif(rec) for rec in qry.all()]
        logger.info("_get_last_classif_history qry: %d rows", len(ret))
        return ret

    def revert_to_history(self, from_user_id: Optional[int], but_not_from_user_id: Optional[int]) \
            -> List[HistoricalLastClassif]:
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
            -> List[HistoricalLastClassif]:
        """
            Same as @see revert_to_history but don't commit the changes, just return them.
        """
        histo = self._get_last_classif_history(from_user_id, but_not_from_user_id)
        return histo

    def classify_validate(self, user_id: UserIDT, classif_ids: ClassifIDListT, wanted_qualif: str) \
            -> Tuple[int, Dict[Tuple, ObjectIDListT]]:
        """
            Set current classifications in self and/or validate current classification.
            :param user_id: The User who did these changes.
            :param classif_ids: One category id for each of the object ids in self. -1 means "keep current".
            :param wanted_qualif: V(alidate) or D(ubious). Use "=" for keeping same qualification.
            :returns updated rows and a summary of changes, for MRU and logging.
        """
        # Gather state of classification, for impacted objects, before the change. Keep a lock on rows.
        present = self._fetch_classifs_and_lock()

        # Cook a diff b/w present and wanted values, both for the update of obj_head and preparing the ones on _stat
        # Group the updates as lots of them are identical
        updates: Dict[Tuple, EnumeratedObjectSet] = {}
        all_changes: OrderedDict[Tuple, List[int]] = OrderedDict()
        target_qualif = wanted_qualif
        # A bit of obsessive optimization
        classif_id_col = ObjectHeader.classif_id.name
        classif_qual_col = ObjectHeader.classif_qual.name
        classif_who_col = ObjectHeader.classif_who.name
        classif_when_col = ObjectHeader.classif_when.name
        for obj_id, v in zip(self.object_ids, classif_ids):
            prev_obj = present[obj_id]
            prev_classif_id: Optional[int] = prev_obj['classif_id']
            new_classif_id: Optional[int]
            if v == -1:  # special value from validate all
                # Arrange that no change can happen for this field
                # Note: prev_classif_id can be None
                new_classif_id = prev_classif_id
            else:
                new_classif_id = v
            prev_classif_qual = prev_obj['classif_qual']
            if wanted_qualif == '=':  # special value for 'keep current qualification'
                # Arrange that no change can happen for this field
                target_qualif = prev_classif_qual
            if (prev_classif_id == new_classif_id
                    and prev_classif_qual == target_qualif
                    and prev_obj['classif_who'] == user_id):
                continue
            # There was at least 1 field change for this object
            an_update = updates.setdefault((new_classif_id, target_qualif), EnumeratedObjectSet(self.session, []))
            an_update.add_object(obj_id)
            # Compact changes, grouped by operation
            change_key = (prev_classif_id, prev_classif_qual, new_classif_id, target_qualif)
            for_this_change = all_changes.setdefault(change_key, [])
            for_this_change.append(obj_id)
            # Keep the recently used in first
            all_changes.move_to_end(change_key, last=False)

        if len(updates) == 0:
            # Nothing to do
            return 0, all_changes

        # Update of obj_head, grouped by similar operations.
        nb_updated = 0
        sql_now = text("now()")
        for (new_classif_id, new_wanted_qualif), an_obj_set in updates.items():
            # Historize the updated rows (can be a lot!)
            an_obj_set.historize_classification(only_qual=None, manual=True)
            row_upd = {classif_id_col: new_classif_id,
                       classif_qual_col: new_wanted_qualif,
                       classif_who_col: user_id,
                       classif_when_col: sql_now}
            # Do the update itsef
            nb_updated += an_obj_set.update_all(row_upd)

        logger.info("%d rows updated in %d queries", nb_updated, len(updates))

        # Return statuses
        return nb_updated, all_changes

    def classify_auto(self, classif_ids: ClassifIDListT, scores: List[float], keep_logs: bool) \
            -> Tuple[int, Dict[Tuple, ObjectIDListT]]:
        """
            Set automatic classifications in self.
            :param classif_ids: One category id for each of the object ids in self.
            :param scores: One confidence score for each object from automatic classification algorithm.
            :param keep_logs: Self-explained
            :returns updated rows and a summary of changes, for stats.
        """
        # Gather state of classification, for impacted objects, before the change. Keep a lock on rows.
        prev = self._fetch_classifs_and_lock()

        # Cook a diff b/w present and wanted values, both for the update of obj_head and preparing the ones on _stat
        # updates: Dict[Tuple, EnumeratedObjectSet] = {}
        all_changes: OrderedDict[Tuple, List[int]] = OrderedDict()
        # A bit of obsessive optimization
        classif_auto_id_col = ObjectHeader.classif_auto_id.name
        classif_auto_score_col = ObjectHeader.classif_auto_score.name
        classif_id_col = ObjectHeader.classif_id.name
        classif_qual_col = ObjectHeader.classif_qual.name
        overriden_by_prediction = {None, PREDICTED_CLASSIF_QUAL}
        full_updates = []
        partial_updates = []
        objid_param = "_objid"
        for obj_id, classif, score in zip(self.object_ids, classif_ids, scores):
            prev_obj = prev[obj_id]
            prev_classif_id: Optional[int] = prev_obj['classif_id']
            prev_classif_qual = prev_obj['classif_qual']
            # Whatever, set the auto_* fields
            an_update: Dict[str, Any] = {objid_param: obj_id,
                                         classif_auto_id_col: classif,
                                         classif_auto_score_col: score}
            if prev_classif_qual in overriden_by_prediction:
                # If not manually modified, go to Predicted state and set prediction as classification
                an_update[classif_id_col] = classif
                an_update[classif_qual_col] = PREDICTED_CLASSIF_QUAL
                full_updates.append(an_update)
                change_key = (prev_classif_id, prev_classif_qual, classif, PREDICTED_CLASSIF_QUAL)
                # Compact changes, grouped by operation
                for_this_change = all_changes.setdefault(change_key, [])
                for_this_change.append(obj_id)
            else:
                # Just store prediction, no change on user-visible data
                partial_updates.append(an_update)

        # Historize (auto)
        if keep_logs:
            self.historize_classification(only_qual=None, manual=True)

        # Bulk (or sort of) update of obj_head
        sql_now = text("now()")
        obj_upd_qry: Update = ObjectHeader.__table__.update()
        obj_upd_qry = obj_upd_qry.where(ObjectHeader.objid == bindparam(objid_param))
        nb_updated = 0
        if len(full_updates) > 0:
            full_upd_qry = obj_upd_qry.values(classif_id=bindparam(classif_id_col),
                                              classif_qual=bindparam(classif_qual_col),
                                              classif_auto_id=bindparam(classif_auto_id_col),
                                              classif_auto_score=bindparam(classif_auto_score_col),
                                              classif_auto_when=sql_now)
            nb_updated += self.session.execute(full_upd_qry, full_updates).rowcount
        # Partial updates
        if len(partial_updates) > 0:
            part_upd_qry = obj_upd_qry.values(classif_auto_id=bindparam(classif_auto_id_col),
                                              classif_auto_score=bindparam(classif_auto_score_col),
                                              classif_auto_when=sql_now)
            nb_updated += self.session.execute(part_upd_qry, partial_updates).rowcount
        # TODO: Cache upd
        logger.info("_auto: %d and %d gives %d rows updated ", len(full_updates), len(partial_updates), nb_updated)

        # Return statuses
        return nb_updated, all_changes

    def _fetch_classifs_and_lock(self) -> Dict[int, Dict]:
        """
            Fetch, and DB lock, self's objects
        :return:
        """
        qry = select([ObjectHeader.objid,
                      ObjectHeader.classif_auto_id, ObjectHeader.classif_auto_when, ObjectHeader.classif_auto_score,
                      ObjectHeader.classif_id, ObjectHeader.classif_qual,
                      ObjectHeader.classif_who, ObjectHeader.classif_when]).with_for_update(key_share=True)
        qry = qry.where(ObjectHeader.objid == any_(self.object_ids))
        logger.info("Fetch with lock: %s", qry)
        res: Result = self.session.execute(qry)
        prev = {rec['objid']: rec for rec in res.fetchall()}
        return prev


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
        self.status_filter: Optional[str] = filters.get("statusfilter", "")
        self.MapN: Optional[Decimal] = self._str_to_decimal(filters, "MapN")
        self.MapW: Optional[Decimal] = self._str_to_decimal(filters, "MapW")
        self.MapE: Optional[Decimal] = self._str_to_decimal(filters, "MapE")
        self.MapS: Optional[Decimal] = self._str_to_decimal(filters, "MapS")
        self.depth_min: Optional[Decimal] = self._str_to_decimal(filters, "depthmin")
        self.depth_max: Optional[Decimal] = self._str_to_decimal(filters, "depthmax")
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
        self.free_num_start: Optional[Decimal] = self._str_to_decimal(filters, "freenumst")
        self.free_num_end: Optional[Decimal] = self._str_to_decimal(filters, "freenumend")
        # Free text filtering
        self.free_text: Optional[str] = filters.get("freetxt", '')
        self.free_text_val: Optional[str] = filters.get("freetxtval", "")
        # A coma-separated list of numerical user ids
        self.annotators: Optional[str] = filters.get('filt_annot', '')
        # Only the last annotator, unlike "filt_annot" which digs in history
        self.last_annotators: Optional[str] = filters.get('filt_last_annot', '')

    def category_id_only(self) -> Optional[ClassifIDT]:
        """
            If, and only if, the filter is on a single taxon, return its identifier
        """
        if self.samples:
            return None

        if self.status_filter:
            return None

        if self.MapN or self.MapW or self.MapE or self.MapS:
            return None

        if self.depth_min or self.depth_max:
            return None

        if self.instrument:
            return None

        if self.daytime:
            return None

        if self.months:
            return None

        if self.from_date:
            return None

        if self.to_date:
            return None

        if self.invert_time or self.from_time or self.to_time:
            return None

        if self.validated_from:
            return None

        if self.validated_to:
            return None

        if self.free_num or self.free_num_start:
            return None

        if self.free_num or self.free_num_end:
            return None

        if self.free_text or self.free_text_val:
            return None

        if self.annotators or self.last_annotators:
            return None

        if self.taxo_child:
            return None

        if self.taxo:
            cats = [int(x) for x in self.taxo.split(',')]
            if len(cats) == 1:
                return cats[0]

        return None

    @staticmethod
    def _str_to_decimal(a_dict: ProjectFilters, a_key: str) -> Optional[Decimal]:
        # noinspection PyTypedDict
        val = a_dict.get(a_key, '')
        if val:
            assert isinstance(val, str)  # for mypy
            return Decimal(val)
        else:
            return None

    def get_sql_filter(self, where_clause: WhereClause, params: SQLParamDict, user_id: int) -> None:
        """
            The generated SQL assumes that, in the query:
                'obh' is the alias for object_head aka ObjectHeader
                'obf' the alias for ObjectFields
                'acq' is the alias for Acquisition
                'sam' is the alias for Sample
        :param user_id: For filtering validators.
        :param where_clause: SQL filtering clauses on objects will be added there.
        :param params: SQL params will be added there.
        :return:
        """

        # Hierarchy first
        if self.samples:
            samples_ids = [int(x) for x in self.samples.split(',')]
            where_clause *= "sam.sampleid = ANY (:samples)"
            params['samples'] = samples_ids

        if self.taxo:
            where_clause *= "obh.classif_id = ANY (:taxo)"
            if self.taxo_child:
                # TODO: Cache if used
                params['taxo'] = list(TaxonomyBO.children_of(self.session, [int(self.taxo)]))
            else:
                params['taxo'] = [int(x) for x in self.taxo.split(',')]

        if self.status_filter:
            if self.status_filter == "NV":
                where_clause *= "(obh.classif_qual != '%s' OR obh.classif_qual IS NULL)" % VALIDATED_CLASSIF_QUAL
            elif self.status_filter == "PV":
                where_clause *= "obh.classif_qual IN ('%s','%s')" % (VALIDATED_CLASSIF_QUAL, PREDICTED_CLASSIF_QUAL)
            elif self.status_filter == "NVM":
                where_clause *= "obh.classif_qual = '%s'" % VALIDATED_CLASSIF_QUAL
                where_clause *= "obh.classif_who != " + str(user_id)
            elif self.status_filter == "VM":
                where_clause *= "obh.classif_qual = '%s'" % VALIDATED_CLASSIF_QUAL
                where_clause *= "obh.classif_who = " + str(user_id)
            elif self.status_filter == "U":
                where_clause *= "obh.classif_qual IS NULL"
            else:
                where_clause *= "obh.classif_qual = '" + self.status_filter + "'"

        if self.MapN and self.MapW and self.MapE and self.MapS:
            where_clause *= "obh.latitude BETWEEN :MapS AND :MapN"
            where_clause *= "obh.longitude BETWEEN :MapW AND :MapE"
            params['MapN'] = self.MapN
            params['MapW'] = self.MapW
            params['MapE'] = self.MapE
            params['MapS'] = self.MapS

        if self.depth_min and self.depth_max:
            where_clause *= "obh.depth_min BETWEEN :depthmin AND :depthmax"
            where_clause *= "obh.depth_max BETWEEN :depthmin AND :depthmax"
            params['depthmin'] = self.depth_min
            params['depthmax'] = self.depth_max

        if self.instrument:
            where_clause *= "acq.instrument ILIKE :instrum "
            params['instrum'] = '%' + self.instrument + '%'

        if self.daytime:
            where_clause *= "obh.sunpos = ANY (:daytime)"
            params['daytime'] = [x for x in self.daytime.split(',')]

        if self.months:
            where_clause *= "EXTRACT(month FROM obh.objdate) = ANY (:month)"
            params['month'] = [int(x) for x in self.months.split(',')]

        if self.from_date:
            where_clause *= "obh.objdate >= TO_DATE(:fromdate,'YYYY-MM-DD')"
            params['fromdate'] = self.from_date

        if self.to_date:
            where_clause *= "obh.objdate <= TO_DATE(:todate,'YYYY-MM-DD')"
            params['todate'] = self.to_date

        if self.invert_time:
            if self.from_time and self.to_time:
                where_clause *= "(obh.objtime <= time :fromtime OR obh.objtime >= time :totime)"
                params['fromtime'] = self.from_time
                params['totime'] = self.to_time
        else:
            if self.from_time:
                where_clause *= "obh.objtime >= time :fromtime"
                params['fromtime'] = self.from_time
            if self.to_time:
                where_clause *= "obh.objtime <= time :totime"
                params['totime'] = self.to_time

        if self.validated_from:
            where_clause *= "obh.classif_when >= TO_TIMESTAMP(:validfromdate,'YYYY-MM-DD HH24:MI')"
            params['validfromdate'] = self.validated_from

        if self.validated_to:
            where_clause *= "obh.classif_when <= TO_TIMESTAMP(:validtodate,'YYYY-MM-DD HH24:MI')"
            params['validtodate'] = self.validated_to

        if self.free_num and self.free_num_start:
            criteria_col = "n%02d" % int(self.free_num[2:])
            where_clause *= "obf." + criteria_col + " >= :freenumst"
            params['freenumst'] = self.free_num_start

        if self.free_num and self.free_num_end:
            criteria_col = "n%02d" % int(self.free_num[2:])
            where_clause *= "obf." + criteria_col + " <= :freenumend"
            params['freenumend'] = self.free_num_end

        if self.free_text and self.free_text_val:
            criteria_tbl = self.free_text[0]
            criteria_col = "t%02d" % int(self.free_text[2:])
            if criteria_tbl == 'o':
                where_clause *= "obf." + criteria_col + " ILIKE :freetxtval"
            elif criteria_tbl == 'a':
                where_clause *= "acq." + criteria_col + " ILIKE :freetxtval"
            elif criteria_tbl == 's':
                where_clause *= "sam." + criteria_col + " ILIKE :freetxtval "
            elif criteria_tbl == 'p':
                where_clause *= "prc." + criteria_col + " ILIKE :freetxtval "
            like_exp = '%' + self.free_text_val + '%'
            # Apply standard BOL/EOL regexp markers
            if like_exp[:2] == "%^":  # Exact match at beginning
                like_exp = like_exp[2:]
            if like_exp[-2:] == "$%":  # Exact match at end
                like_exp = like_exp[:-2]
            params['freetxtval'] = like_exp

        if self.annotators:
            where_clause *= "(obh.classif_who = ANY (:filt_annot) " \
                            " OR exists (SELECT och.classif_who " \
                            "              FROM " + ObjectsClassifHisto.__tablename__ + " och " + \
                            "             WHERE och.objid = obh.objid " \
                            "               AND och.classif_who = ANY (:filt_annot) ) )"
            params['filt_annot'] = [int(x) for x in self.annotators.split(',')]
        elif self.last_annotators:
            where_clause *= "obh.classif_who = ANY (:filt_annot)"
            params['filt_annot'] = [int(x) for x in self.last_annotators.split(',')]
