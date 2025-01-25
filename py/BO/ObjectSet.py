# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A set of Object as seen by the user, e.g. on classification page.
#
# The set comprises all objects from a Project, except the ones filtered by a set of criteria.
#
from __future__ import annotations

import datetime
from collections import OrderedDict
from decimal import Decimal
from typing import (
    Tuple,
    Optional,
    List,
    Iterator,
    Callable,
    Dict,
    Any,
    OrderedDict as OrderedDictT,
    cast,
    Final,
)

# A Postgresl insert generator, needed for the key conflict clause
from sqlalchemy import bindparam
from sqlalchemy.sql import Alias

from API_models.filters import ProjectFiltersDict
from BO.Classification import (
    HistoricalLastClassif,
    ClassifIDListT,
    ClassifIDT,
    ClassifScoresListT,
)
from BO.ColumnUpdate import ColUpdateList
from BO.Mappings import (
    ProjectMapping,
    ProjectSetMapping,
    TableMapping,
    TABLE_TO_PREFIX,
    FREE_COLS_ARE_ELSEWHERE,
)
from BO.Object import ObjectIDWithParentsT, MANUAL_STATES_TEXT, PREDICTED_STATE_TEXT
from BO.Taxonomy import TaxonomyBO
from BO.Training import TrainingBO, PredictionBO
from BO.User import UserIDT
from BO.helpers.MappedTable import MappedTable
from DB import Session, Query, Process, Taxonomy, User
from DB.Acquisition import Acquisition
from DB.Image import Image
from DB.Object import (
    ObjectsClassifHisto,
    ObjectFields,
    PREDICTED_CLASSIF_QUAL,
    VALIDATED_CLASSIF_QUAL,
    ObjectHeader,
    ObjectIDT,
    NON_UPDATABLE_VIA_API,
    DUBIOUS_CLASSIF_QUAL,
    ObjectIDListT,
)
from DB.Prediction import (
    PSEUDO_TRAINING_SCORE,
)
from BO.Project import ProjectBOSet, ProjectBO
from DB.Project import ProjectIDListT, Project
from DB.Sample import Sample
from DB.helpers import Result
from DB.helpers.Core import select
from DB.helpers.Direct import func
from DB.helpers.ORM import Row, Delete, Update, any_, and_, or_, case
from DB.helpers.Postgres import pg_insert, PgInsert
from DB.helpers.SQL import WhereClause, SQLParamDict, FromClause, OrderClause
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

# Typings, to be clear that these are not e.g. project IDs
# Object_id + parents + project
ObjectIDWithParentsListT = List[ObjectIDWithParentsT]
# Previous classif, previous qual, next classif, next qual
ChangeTupleT = Tuple[Optional[int], str, int, str]
# Many changes, each of them applied to many objects
ObjectSetClassifChangesT = OrderedDictT[ChangeTupleT, ObjectIDListT]

logger = get_logger(__name__)

# If one of these statuses are required, then the classif_id must be valid
MEANS_CLASSIF_ID_EXIST = ("P", "V", "D", "PV", "PVD", "NVM", "VM")
# MEANS_TRAINING_ID_EXIST = ("P",)
NO_HISTO = "n"


class DescribedObjectSet(object):
    """
    A (potentially large) set of objects, described by a base rule (all objects in project XXX)
    and filtered by exclusion conditions.
    """

    __slots__ = ("prj", "user_id", "mapping", "filters")

    def __init__(
        self,
        session: Session,
        prj: Project,
        user_id: Optional[UserIDT],
        filters: ProjectFiltersDict,
    ):
        """
        :param user_id: The 'current' user, in case the filter refers to him/her.
        """
        self.prj = prj
        self.user_id = user_id
        self.mapping = ProjectMapping().load_from_project(prj)
        self.filters = ObjectSetFilter(session, filters)

    def get_sql(
        self,
        order_clause: Optional[OrderClause] = None,
        select_list: str = "",
        all_images: bool = False,
    ) -> Tuple[FromClause, WhereClause, SQLParamDict]:
        """
        Construct SQL parts for getting per-object information.
        :param order_clause: The required order by clause, possibly containing a resultset window.
        :param select_list: Used for hinting the builder that some specific table will be needed in join.
                major tables obj_head, samples and acquisitions are always joined.
        :param all_images: If not set (default), only return the lowest rank, i.e. visible, image
        :return:
        """
        if order_clause is None:
            order_clause = OrderClause()
        # The filters on objects
        obj_where = WhereClause()
        params: SQLParamDict = {"projid": self.prj.projid}
        self.filters.get_sql_filter(
            obj_where, params, self.user_id, self.mapping.object_mappings
        )
        column_referencing_sql = (
            select_list + obj_where.get_sql() + order_clause.get_sql()
        )
        selected_tables = FromClause(
            f"(select (:projid) as projid) prjs"
        )  # Prepare a future _set_ of projects
        if "prj." in column_referencing_sql:
            selected_tables += (
                f"{Project.__tablename__} prj ON prj.projid = prjs.projid"
            )
            selected_tables += f"{Sample.__tablename__} sam ON sam.projid = prj.projid"
        else:
            selected_tables += f"{Sample.__tablename__} sam ON sam.projid = prjs.projid"
        selected_tables += (
            f"{Acquisition.__tablename__} acq ON acq.acq_sample_id = sam.sampleid"
        )
        if "prc." in column_referencing_sql:
            selected_tables += (
                f"{Process.__tablename__} prc ON prc.processid = acq.acquisid"
            )
        obj_field_joined = "obf." in column_referencing_sql
        if obj_field_joined and self.driving_table_is_obj_field(
            obj_where.get_sql(),
            order_clause.get_sql(),
        ):
            selected_tables += (
                f"{ObjectFields.__tablename__} obf ON obf.acquis_id = acq.acquisid"
            )
            selected_tables += (
                f"{ObjectHeader.__tablename__} obh ON obh.objid = obf.objfid"
            )
        else:
            selected_tables += (
                f"{ObjectHeader.__tablename__} obh ON obh.acquisid = acq.acquisid"
            )
            if obj_field_joined:
                selected_tables += (
                    f"{ObjectFields.__tablename__} obf ON obf.objfid = obh.objid"
                )
        # if "prd." in column_referencing_sql:
        #     preds_ref = Prediction.__tablename__ + " prd"
        #     selected_tables += (
        #         preds_ref
        #         + " ON prd.object_id = obh.objid AND prd.classif_id = obh.classif_id"
        #     )
        #     if self.filters.status_filter not in MEANS_TRAINING_ID_EXIST:
        #         selected_tables.set_outer(preds_ref)
        # if "trn." in column_referencing_sql:
        #     trainings_ref = Training.__tablename__ + " trn"
        #     selected_tables += trainings_ref + " ON trn.training_id = prd.training_id"
        #     if self.filters.status_filter not in MEANS_TRAINING_ID_EXIST:
        #         selected_tables.set_outer(trainings_ref)
        if "ohu." in column_referencing_sql:  # Inline query for annotators in history
            selected_tables += (
                f"(select 1 as in_annots WHERE EXISTS (select * from {ObjectsClassifHisto.__tablename__} och "
                "WHERE och.objid = obh.objid AND och.classif_who = ANY (:filt_annot) ) ) ohu ON True"
            )
            selected_tables.set_outer("(select 1 as in_annots ")
            selected_tables.set_lateral("(select 1 as in_annots ")
        if "txo." in column_referencing_sql or "txp." in column_referencing_sql:
            selected_tables += (
                f"{Taxonomy.__tablename__} txo ON txo.id = obh.classif_id"
            )
            if (
                self.filters.status_filter not in MEANS_CLASSIF_ID_EXIST
                and not self.filters.taxo  # If some taxo is needed it's a plain join
            ):
                selected_tables.set_outer(f"{Taxonomy.__tablename__} txo ")
        if "img." in column_referencing_sql:
            selected_tables += (
                f"{Image.__tablename__} img ON obh.objid = img.objid "
                if all_images
                else f"(select * from {Image.__tablename__} img2 where obh.objid = img2.objid order by imgrank limit 1) img ON true"
            )
            selected_tables.set_lateral(f"(select * from {Image.__tablename__}")
        if "usr." in column_referencing_sql:
            selected_tables += f"{User.__tablename__} usr ON obh.classif_who = usr.id"
            selected_tables.set_outer(f"{User.__tablename__} usr ")
        if "txp." in column_referencing_sql:
            selected_tables += f"{Taxonomy.__tablename__} txp ON txp.id = txo.parent_id"
            selected_tables.set_outer(f"{Taxonomy.__tablename__} txp ")
        return selected_tables, obj_where, params

    def without_filtering_taxo(self):
        """
        Return a clone of self, but without any Taxonomy related filter.
        """
        filters_but_taxo = self.filters.filters_without_taxo()
        return DescribedObjectSet(
            self.filters.session, self.prj, self.user_id, filters_but_taxo
        )

    def driving_table_is_obj_field(self, where: str, order: str) -> bool:
        """Choose the fastest way to find needed objects.
        We mirror acquis_id from obj_head to obj_fields so 2 options are:
        -1 Fetch via acquis_id the big rows in obj_fields and then PK access to obj_head
        -2 Fetch via acquis_id the small rows in obj_head and then PK access to obj_fields
        1 is faster if we need the majority of rows, 2 is better if some filter eliminates based on obj_head cols.
        We don't know in advance the selectivity of filters, so there is kind of heuristic here.
        """
        ret = False
        if ("obf." in order) or ("obf." in where and "obh." not in where):
            ret = True
        if (
            "obh.classif_id" in where
        ):  # Very discriminating and covered by index 'is_objectsacqclassifqual'
            ret = False
        if (
            "obh.classif_qual" in where  # covered as well by 'is_objectsacqclassifqual'
            and self.filters.status_filter
            not in ("NV",)  # This OR-linked condition does not end up in index scan
        ):
            ret = False
        return ret


class EnumeratedObjectSet(MappedTable):
    """
    A set of objects, described by all their IDs.
    """

    def __init__(self, session: Session, object_ids: ObjectIDListT):
        super().__init__(session)
        assert isinstance(object_ids, list)
        assert len(object_ids) == 0 or isinstance(object_ids[0], ObjectIDT)
        self.object_ids = object_ids

    def add_object(self, object_id: ObjectIDT) -> None:
        self.object_ids.append(object_id)

    def __len__(self) -> int:
        return len(self.object_ids)

    def get_objectid_chunks(self, chunk_size: int) -> Iterator[ObjectIDListT]:
        """
        Yield successive n-sized chunks from l.
        Adapted from
        https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks/312464#312464
        """
        lst = self.object_ids
        for idx in range(0, len(lst), chunk_size):
            yield lst[idx : idx + chunk_size]

    def get_projects_ids(self) -> ProjectIDListT:
        """
        Return the project IDs for the owned objectsIDs.
        """
        qry = self.session.query(Project.projid).distinct(Project.projid)
        qry = qry.join(Sample)
        qry = qry.join(Acquisition)
        qry = qry.join(ObjectHeader)
        qry = qry.filter(ObjectHeader.objid == any_(self.object_ids))
        with CodeTimer("Prjs for %d objs: " % len(self.object_ids), logger):
            return [an_id for an_id, in qry]

    @staticmethod
    def _delete_chunk(
        session: Session, a_chunk: ObjectIDListT
    ) -> Tuple[int, int, List[str]]:
        """
        Delete a chunk from self's object list.
        Technical Note: We use SQLA Core as we don't want to fetch the ORM entities
        """
        # Start with physical images, which are not deleted via a CASCADE on DB side
        # This is maybe due to relationship cycle b/w ObjectHeader and Images @See comment in Image class
        img_del_qry: Delete = Image.__table__.delete()
        img_del_qry = img_del_qry.where(Image.objid == any_(a_chunk))
        img_del_qry = img_del_qry.returning(
            Image.imgid, Image.orig_file_name, Image.thumb_height
        )
        img_from_id_and_orig = Image.img_from_id_and_orig
        thumb_img_from_id_and_orig = Image.thumb_img_from_id_if_there
        with CodeTimer("DELETE for %d images: " % len(a_chunk), logger):
            files_res = session.execute(img_del_qry)
            img_files = []
            nb_img_rows = 0
            for imgid, orig_file_name, thumb_height in files_res:
                main_img_file, thumb_img_file = img_from_id_and_orig(
                    imgid, orig_file_name
                ), thumb_img_from_id_and_orig(imgid, thumb_height)
                # We have main file and optionally the thumbnail one
                img_files.append(main_img_file)
                if thumb_img_file is not None:
                    img_files.append(thumb_img_file)
                nb_img_rows += 1
            logger.info(
                "Removed: %d rows, to remove: %d files", nb_img_rows, len(img_files)
            )

        obj_del_qry: Delete = ObjectHeader.__table__.delete()
        obj_del_qry = obj_del_qry.where(ObjectHeader.objid == any_(a_chunk))
        with CodeTimer("DELETE for %d objs: " % len(a_chunk), logger):
            nb_objs = session.execute(obj_del_qry).rowcount  # type:ignore # case1

        session.commit()
        # TODO: Cache delete
        return nb_objs, nb_img_rows, img_files

    def delete(
        self, chunk_size: int, do_with_files: Optional[Callable[[List[str]], None]]
    ) -> Tuple[int, int, List[str]]:
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

    def force_to_predicted(
        self, training: TrainingBO
    ) -> Tuple[int, ObjectSetClassifChangesT]:
        """
        Force to Predicted state, keeping log, i.e. history, of current state.
        Only Validated and Dubious states are affected, the goal being to bring
        the whole set of objects to a Predict-able state.
        A pseudo-training is created with conventional score per object.
        """
        classif_id_lists = []
        classif_score_lists = []
        # Create pseudo-predictions for the training
        qry = self.session.query(
            ObjectHeader.objid,
            ObjectHeader.classif_id,
        )
        qry = qry.filter(ObjectHeader.objid == any_(self.object_ids))
        qry = qry.filter(ObjectHeader.classif_qual.in_(MANUAL_STATES_TEXT))
        # A bit dirty but fast
        prev_nb_objs = len(self.object_ids)
        new_objects_ids = []
        for rec in qry:
            new_objects_ids.append(rec["objid"])
            classif_id_lists.append([rec["classif_id"]])  # Single-elem list
            classif_score_lists.append([PSEUDO_TRAINING_SCORE])  # Ditto

        # Classify with new training
        self.object_ids = new_objects_ids
        nb_upd, all_changes = self.classify_auto_mult(
            training, classif_id_lists, classif_score_lists, True
        )

        # TODO: Cache upd
        logger.info(
            " %d out of %d rows forced to predicted", len(self.object_ids), prev_nb_objs
        )

        return nb_upd, all_changes

    def update_all(self, params: Dict[str, Any]) -> int:
        """
        Update all self's objects using given parameters, dict of column names and values.
        """
        # Update objects table
        obj_upd_qry: Update = ObjectHeader.__table__.update()
        obj_upd_qry = obj_upd_qry.where(ObjectHeader.objid == any_(self.object_ids))
        obj_upd_qry = obj_upd_qry.values(params)
        updated_objs = self.session.execute(
            obj_upd_qry
        ).rowcount  # type:ignore  # case1
        # TODO: Cache upd
        # prj_id = self.get_projects_ids()[0]
        # ObjectCacheUpdater(prj_id).update_objects(self.object_ids, params)
        return cast(int, updated_objs)

    def historize_classification(self, only_qual: Optional[List[str]]) -> int:
        """
        Copy current classification information into history table, for all rows in self.
        :param only_qual: If set, only historize for current rows with this classification.
        """
        # Light up a bit the SQLA expressions
        oh = ObjectHeader
        och = ObjectsClassifHisto
        #
        # No classif_qual AKA state: Assume there is nothing to log.
        #
        # 'P' state: classif_id contains the user-visible category, referenced in the training via predictions.
        #
        # 'V' and 'D' states: classif_id contains the user-chosen category, which can be either the
        #                     last predicted classif_id, or not if another category was assigned in the UI.
        #                     There is no specific code for 'accept prediction', there is some code convention
        #                     for 'validate current' (-1 as target_qualif) but it's not visible in DB.
        #

        # What's inserted, both cases, into the history table -- all columns
        ins_columns = [
            och.objid,  # <- oh.objid
            och.classif_qual,  # <- oh.classif_qual
            och.classif_id,  # <- oh.classif_id
            och.classif_date,  # <- oh.classif_date date of last transition.
            och.classif_who,  # <- oh.classif_who
            och.classif_score,  # <- oh.classif_score
        ]
        # What we want to historize, as a subquery - The current state
        sel_subqry = select(
            [
                oh.objid,
                oh.classif_qual,
                oh.classif_id,
                oh.classif_date,
                oh.classif_who,  # Is NULL when 'P' or initial
                oh.classif_score,  # Is NULL when not 'P'
            ]
        )
        if only_qual is not None:
            # Pick only the required states # TODO: Unused, to keep?
            qual_cond = oh.classif_qual.in_(only_qual)
        else:
            # Pick any present state
            qual_cond = oh.classif_qual.isnot(None)
        sel_subqry = sel_subqry.where(
            and_(oh.objid == any_(self.object_ids), qual_cond)
        )
        # Insert into the log table
        ins_qry: PgInsert = pg_insert(och.__table__)
        ins_qry = ins_qry.from_select(ins_columns, sel_subqry)
        # TODO: Below not clear nor clean
        ins_qry = ins_qry.on_conflict_do_nothing(constraint="objectsclassifhisto_pkey")
        # logger.info("Histo query: %s", ins_qry.compile())
        nb_obj_histos = self.session.execute(ins_qry).rowcount  # type:ignore  # case1
        logger.info(
            " %d out of %d rows copied to log", nb_obj_histos, len(self.object_ids)
        )
        return nb_obj_histos

    def apply_on_all(self, project: Project, updates: ColUpdateList) -> int:
        """
        Apply all updates on all objects pointed at by the list.
        """
        mapped_updates = []
        direct_updates = []
        for an_upd in updates.lst:
            dest_col = an_upd["ucol"]
            if dest_col in ObjectHeader.__dict__:
                if dest_col in NON_UPDATABLE_VIA_API:
                    continue
                direct_updates.append(an_upd)
            else:
                mapped_updates.append(an_upd)
        # Return
        return max(
            self._apply_on_all_non_mapped(ObjectHeader, direct_updates),
            self._apply_on_all(ObjectFields, project, mapped_updates),
        )

    def add_filter(self, upd: Query) -> Query:
        if ObjectHeader.__tablename__ + "." in str(upd):
            ret = upd.filter(ObjectHeader.objid == any_(self.object_ids))
        else:
            ret = upd.filter(ObjectFields.objfid == any_(self.object_ids))
        return ret

    def _get_last_classif_history(
        self, from_user_id: Optional[int], but_not_from_user_id: Optional[int]
    ) -> List[HistoricalLastClassif]:
        """
        Query for last classification history on all objects of self.
        """
        # Get the historical entries
        subqry = self.session.query(
            ObjectsClassifHisto,
            func.rank()
            .over(
                partition_by=ObjectsClassifHisto.objid,
                order_by=ObjectsClassifHisto.classif_date.desc(),
            )
            .label("rnk"),
        )
        if from_user_id:
            subqry = subqry.filter(ObjectsClassifHisto.classif_who == from_user_id)
            # Pick Manual logs from this user
            subqry = subqry.filter(
                ObjectsClassifHisto.classif_qual.in_(MANUAL_STATES_TEXT)
            )
        if but_not_from_user_id:
            subqry = subqry.filter(
                or_(
                    ObjectsClassifHisto.classif_who != but_not_from_user_id,
                    ObjectsClassifHisto.classif_who == None,
                )
            )
        subq_alias: Alias = subqry.filter(
            ObjectsClassifHisto.objid == any_(self.object_ids)
        ).subquery()

        # We have a maximum of 1 line from ObjectsClassifHisto (the one with most recent date) from subquery
        qry = self.session.query(
            ObjectHeader.objid,
            ObjectHeader.classif_id,
            subq_alias.c.classif_date.label("histo_classif_date"),
            case(  # Emulate previous value
                [
                    (subq_alias.c.classif_qual.in_(MANUAL_STATES_TEXT), "M"),
                    (subq_alias.c.classif_qual == PREDICTED_STATE_TEXT, "A"),
                ]
            ).label("histo_classif_type"),
            func.coalesce(
                subq_alias.c.classif_qual,
                NO_HISTO,
            ).label("histo_classif_qual"),
            subq_alias.c.classif_id.label("histo_classif_id"),
            subq_alias.c.classif_who.label("histo_classif_who"),
            subq_alias.c.classif_score.label("histo_classif_score"),
        )
        qry = qry.join(
            subq_alias,
            ObjectHeader.objid == subq_alias.c.objid,
            isouter=(from_user_id is None),
        )
        if from_user_id is not None:
            # If taking history from a user, don't apply to the objects he/she classified
            # in last already.
            qry = qry.filter(ObjectHeader.classif_who != from_user_id)
            qry = qry.filter(subq_alias.c.rnk == 1)
        else:
            # Taking any history, including nothing, so emit blank history (see isouter above)
            qry = qry.filter(ObjectHeader.objid == any_(self.object_ids))
            qry = qry.filter(or_(subq_alias.c.rnk == 1, subq_alias.c.rnk.is_(None)))
        logger.info("_get_last_classif_history qry:%s", str(qry))
        with CodeTimer("HISTORY for %d objs: " % len(self.object_ids), logger):
            ret = [HistoricalLastClassif(**rec) for rec in qry]
        logger.info("_get_last_classif_history qry: %d rows", len(ret))
        return ret

    def revert_to_history(
        self, from_user_id: Optional[int], but_not_from_user_id: Optional[int]
    ) -> List[HistoricalLastClassif]:
        """
            Update (some of) self's objects so that current classification becomes the last one from hist_user_id,
        :param from_user_id: If set (!= None), the user_id to copy classification from. If unset then pick any recent.
        :param but_not_from_user_id: If set (!= None), exclude this user from history picking.
        """
        histo = self._get_last_classif_history(from_user_id, but_not_from_user_id)
        impacted_objs = [an_histo.objid for an_histo in histo]
        # print("\n".join([str(x) for x in histo]))
        # Bulk update. It's less efficient than a plain update with criteria, but in the future we
        # might be able to do some cherry-picking on the history.
        updates = [
            {
                ObjectHeader.objid.name: an_histo.objid,
                ObjectHeader.classif_qual.name: an_histo.histo_classif_qual,
                ObjectHeader.classif_id.name: an_histo.histo_classif_id,
                ObjectHeader.classif_who.name: an_histo.histo_classif_who,
                ObjectHeader.classif_date.name: an_histo.histo_classif_date,
                ObjectHeader.classif_score.name: an_histo.histo_classif_score,
            }
            for an_histo in histo
            if an_histo.histo_classif_qual != NO_HISTO
        ]
        updates.extend(
            [
                {
                    ObjectHeader.objid.name: an_histo.objid,
                    ObjectHeader.classif_qual.name: None,
                    ObjectHeader.classif_id.name: None,
                    ObjectHeader.classif_who.name: None,
                    ObjectHeader.classif_date.name: None,
                    ObjectHeader.classif_score.name: None,
                }
                for an_histo in histo
                if an_histo.histo_classif_qual == NO_HISTO
            ]
        )
        self.session.bulk_update_mappings(ObjectHeader, updates)
        PredictionBO(self.session, impacted_objs).resurrect_predictions(histo)
        # Ensure the history remains "before present row"
        histo_del_qry: Delete = ObjectsClassifHisto.__table__.delete()
        histo_del_qry = histo_del_qry.where(
            ObjectHeader.objid == ObjectsClassifHisto.objid
        )
        histo_del_qry = histo_del_qry.where(
            ObjectsClassifHisto.classif_date >= ObjectHeader.classif_date
        )
        histo_del_qry = histo_del_qry.where(ObjectHeader.objid == any_(impacted_objs))
        self.session.execute(histo_del_qry)
        self.session.commit()
        return histo

    def evaluate_revert_to_history(
        self, from_user_id: Optional[int], but_not_from_user_id: Optional[int]
    ) -> List[HistoricalLastClassif]:
        """
        Same as @see revert_to_history but don't commit the changes, just return them.
        """
        histo = self._get_last_classif_history(from_user_id, but_not_from_user_id)
        return histo

    def classify_validate(
        self,
        user_id: UserIDT,
        classif_ids: ClassifIDListT,
        wanted_qualif: str,
        log_timestamp: datetime.datetime,
    ) -> Tuple[int, ObjectSetClassifChangesT]:
        """
        Set current classifications in self and/or validate current classification.
        :param user_id: The User who did these changes.
        :param classif_ids: One category id for each of the object ids in self. -1 means "keep current".
        :param wanted_qualif: V(alidate) or D(ubious). Use "=" for keeping same qualification.
        :param log_timestamp: The time to set on objects.
        :returns updated rows and a summary of changes, for MRU and logging.
        """
        # Gather state of classification, for impacted objects, before the change. Keep a lock on rows.
        prev = self._fetch_classifs_and_lock()

        # Cook a diff b/w present and wanted values, both for the update of obj_head and preparing the ones on _stat
        # Group the updates as lots of them are identical
        updates: Dict[Tuple[ClassifIDT, str], EnumeratedObjectSet] = {}
        all_changes: OrderedDict[ChangeTupleT, ObjectIDListT] = OrderedDict()
        target_qualif = wanted_qualif
        # A bit of obsessive optimization, and avoid semantically unbound literal
        (
            classif_id_col,
            classif_qual_col,
            classif_who_col,
            classif_when_col,
            classif_score_col,
        ) = (
            ObjectHeader.classif_id.name,
            ObjectHeader.classif_qual.name,
            ObjectHeader.classif_who.name,
            ObjectHeader.classif_date.name,
            ObjectHeader.classif_score.name,
        )
        for obj_id, wanted in zip(self.object_ids, classif_ids):
            # Present state
            prev_obj = prev[obj_id]
            # Classification change
            prev_classif_id: Optional[int] = prev_obj["classif_id"]
            next_classif_id: Optional[int]
            if wanted == -1:  # special value from "validate as is"
                # Arrange that no change can happen for this field
                # Note: prev_classif_id can be None, e.g. for fresh imports
                next_classif_id = prev_classif_id
            else:
                next_classif_id = wanted
            # Prevent inconsistency, cannot classify to nothing
            if next_classif_id is None:
                continue
            # Classification quality (state) change
            prev_classif_qual = prev_obj["classif_qual"]
            if wanted_qualif == "=":  # special value for 'keep current qualification'
                # Arrange that no change can happen for this field
                target_qualif = prev_classif_qual
            assert target_qualif in (
                VALIDATED_CLASSIF_QUAL,
                DUBIOUS_CLASSIF_QUAL,
            ), "Can't (re)classify Predicted objects, use prediction function"
            # Operator change
            prev_operator_id: Optional[int] = prev_obj["classif_who"]
            if (
                prev_classif_id == next_classif_id
                and prev_classif_qual == target_qualif
                and prev_operator_id == user_id
            ):
                continue
            # There was at least 1 field change for this object
            an_update = updates.setdefault(
                (next_classif_id, target_qualif),
                # Below creates a new group if needed
                EnumeratedObjectSet(self.session, []),
            )
            an_update.add_object(obj_id)
            # Compact changes, grouped by operation
            change_key = (
                prev_classif_id,
                prev_classif_qual,
                next_classif_id,
                target_qualif,
            )
            for_this_change = all_changes.setdefault(change_key, [])
            for_this_change.append(obj_id)
            # Keep the recently used in first
            all_changes.move_to_end(change_key, last=False)

        if len(updates) == 0:
            # Nothing to do
            return 0, all_changes

        # Update of obj_head, grouped by similar operations.
        nb_updated = 0
        for (next_classif_id, new_wanted_qualif), an_obj_set in updates.items():
            # Historize the updated rows (can be a lot!)
            an_obj_set.historize_classification(only_qual=None)
            PredictionBO(self.session, an_obj_set.object_ids).historize_predictions()
            row_upd = {
                classif_id_col: next_classif_id,
                classif_qual_col: new_wanted_qualif,
                classif_when_col: log_timestamp,
                classif_who_col: user_id,
                classif_score_col: None,
            }
            # Do the update itself
            nb_updated += an_obj_set.update_all(row_upd)

        logger.info("%d rows updated in %d queries", nb_updated, len(updates))

        # Return statuses
        return nb_updated, all_changes

    OVERRIDEN_BY_PREDICTION = {
        None,
        PREDICTED_CLASSIF_QUAL,
    }  # Only these states will be overriden

    def classify_auto_mult(
        self,
        training: TrainingBO,
        classif_id_lists: List[ClassifIDListT],
        classif_score_lists: List[ClassifScoresListT],
        force: bool = False,
    ) -> Tuple[int, ObjectSetClassifChangesT]:
        """
        Set automatic classifications in self, keeping a history of previous objects' state.
        ⚠️ There is a strong assumption that below lists are in self.object_ids order ⚠️
        :param training: the operation holder for all predictions.
        :param classif_id_lists: all predicted category ids for each of the object ids in self,
                                from automatic classification algorithm.
        :param classif_score_lists: all predicted confidence scores for each object,
                                from automatic classification algorithm.
        :param force: do not preserve protected states.
        :returns updated rows and a summary of changes, for stats.
        """
        # Gather state of classification, for impacted objects, before the change. Keep a lock on rows.
        prev = self._fetch_classifs_and_lock()

        # Cook a diff b/w present and wanted values, both for the update of obj_head and preparing the ones on _stat
        # updates: Dict[Tuple, EnumeratedObjectSet] = {}
        all_changes: ObjectSetClassifChangesT = OrderedDict()
        # A bit of obsessive optimization, and avoid semantically unbound literal
        (
            objid_col,
            classif_id_col,
            classif_qual_col,
            classif_who_col,
            classif_date_col,
            classif_score_col,
        ) = (
            ObjectHeader.objid.name,
            ObjectHeader.classif_id.name,
            ObjectHeader.classif_qual.name,
            ObjectHeader.classif_who.name,
            ObjectHeader.classif_date.name,
            ObjectHeader.classif_score.name,
        )
        updates: List[Dict[str, Any]] = []

        preds_by_object = (
            PredictionBO(self.session, self.object_ids)
            .historize_predictions()
            .store_predictions(
                training.training_id,
                classif_id_lists,
                classif_score_lists,
            )
        )

        # Prepare updates in the obj_head table
        for obj_id, preds in preds_by_object.items():
            # Present state
            prev_obj = prev[obj_id]
            prev_classif_id: Optional[int] = prev_obj["classif_id"]
            prev_classif_qual = prev_obj["classif_qual"]
            # Wanted possible classifications
            preds.sort(key=lambda t: -t.score)
            # Just override what would not spoil human work, except if explicitly required
            if prev_classif_qual not in self.OVERRIDEN_BY_PREDICTION and not force:
                continue
            # Not manually modified, go to Predicted state and set prediction as classification
            next_classif_id = preds[
                0
            ].classif  # Highest score TODO: remove discarded ones
            next_score = preds[0].score
            an_update: Dict[str, Any] = {
                "_" + objid_col: obj_id,
                classif_qual_col: PREDICTED_CLASSIF_QUAL,
                classif_id_col: next_classif_id,
                classif_who_col: None,
                classif_date_col: training.training_start,
                classif_score_col: next_score,
            }
            updates.append(an_update)
            # Prepare changes, for stats update, grouped by operation
            change_key = (
                prev_classif_id,
                prev_classif_qual,
                next_classif_id,
                PREDICTED_CLASSIF_QUAL,
            )
            for_this_change = all_changes.setdefault(change_key, [])
            for_this_change.append(obj_id)

        # Historize
        changed_object_ids = [
            an_id for chg_ids in all_changes.values() for an_id in chg_ids
        ]
        EnumeratedObjectSet(self.session, changed_object_ids).historize_classification(
            only_qual=None
        )

        # Bulk (or sort of) update of obj_head
        obj_upd_qry: Update = ObjectHeader.__table__.update()
        obj_upd_qry = obj_upd_qry.where(
            ObjectHeader.objid == bindparam("_" + objid_col)
        )
        if len(updates) > 0:
            full_upd_qry = obj_upd_qry.values(
                classif_qual=bindparam(classif_qual_col),
                classif_id=bindparam(classif_id_col),
                classif_who=bindparam(classif_who_col),
                classif_date=bindparam(classif_date_col),
                classif_score=bindparam(classif_score_col),
            )
            self.session.execute(full_upd_qry, updates)
        # Partial updates
        # if len(partial_updates) > 0:
        #     part_upd_qry = obj_upd_qry.values(
        #         pred_id=bindparam(pred_id_col),
        #         classif_auto_when=sql_now,
        #     )
        #     self.session.execute(part_upd_qry, partial_updates)

        # TODO: Cache upd
        logger.info(
            "_auto: %d updates ",
            len(updates),
            # len(partial_updates),
        )
        nb_updated = len(updates)  # + len(partial_updates)
        training.advance()
        # Return statuses
        return nb_updated, all_changes

    def _fetch_classifs_and_lock(self) -> Dict[ObjectIDT, Row]:
        """
        Fetch, and DB lock, self's objects
        """
        qry = select(
            [
                ObjectHeader.objid,
                ObjectHeader.classif_qual,
                ObjectHeader.classif_id,
                ObjectHeader.classif_who,
                ObjectHeader.classif_date,
                ObjectHeader.classif_score,
            ]
        ).with_for_update(key_share=True)
        qry = qry.where(ObjectHeader.objid == any_(self.object_ids))
        logger.info("Fetch with lock: %s", qry)
        res: Result = self.session.execute(qry)
        prev = {rec["objid"]: rec for rec in res.fetchall()}
        return prev


class ObjectSetFilter(object):
    """
    A filter, inside an object set.
    """

    COL_IN_FREE_NUM: Final = {"score": ObjectHeader.classif_score.name}
    TAXO_KEYS: Final = ["taxo", "taxochild"]

    def __init__(self, session: Session, filters: ProjectFiltersDict):
        """
        Init from a dictionary with all fields.
        """
        self.session = session
        self.filters = filters
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
        self.samples: Optional[str] = filters.get("samples", "")
        self.instrument: Optional[str] = filters.get("instrum", "")
        # A coma-separated list of sunpos values
        #  D for Day, U for Dusk, N for Night, A for Dawn (Aube in French)
        self.daytime: Optional[str] = filters.get("daytime", "")
        # A coma-separated list of month numbers
        self.months: Optional[str] = filters.get("month", "")
        self.from_date: Optional[str] = filters.get("fromdate", "")
        self.to_date: Optional[str] = filters.get("todate", "")
        # Time (in day) filters
        self.from_time: Optional[str] = filters.get("fromtime", "")
        self.to_time: Optional[str] = filters.get("totime", "")
        self.invert_time: bool = filters.get("inverttime", "") == "1"
        # Validation date filters
        self.validated_from: Optional[str] = filters.get("validfromdate", "")
        self.validated_to: Optional[str] = filters.get("validtodate", "")
        # Free fields AKA features filtering
        self.free_num: Optional[str] = filters.get("freenum", "")
        self.free_num_start: Optional[Decimal] = self._str_to_decimal(
            filters, "freenumst"
        )
        self.free_num_end: Optional[Decimal] = self._str_to_decimal(
            filters, "freenumend"
        )
        # Free text filtering
        self.free_text: Optional[str] = filters.get("freetxt", "")
        self.free_text_val: Optional[str] = filters.get("freetxtval", "")
        # A coma-separated list of numerical user ids
        self.annotators: Optional[str] = filters.get("filt_annot", "")
        # Only the last annotator, unlike "filt_annot" which digs in history
        self.last_annotators: Optional[str] = filters.get("filt_last_annot", "")

    def category_id_only(self) -> Optional[ClassifIDT]:
        """
        If, and only if, the filter is on a single taxon, return its identifier
        """
        if self.taxo:
            cats = [int(x) for x in self.taxo.split(",")]
            if len(cats) == 1:
                the_one = cats[0]
            else:
                return None
        else:
            return None

        if self.status_filter:
            return None

        if self.samples:
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

        return the_one

        return None

    @staticmethod
    def _str_to_decimal(a_dict: ProjectFiltersDict, a_key: str) -> Optional[Decimal]:
        # noinspection PyTypedDict
        val = a_dict.get(a_key, "")
        if val:
            assert isinstance(val, str)  # for mypy
            return Decimal(val)
        else:
            return None

    def get_sql_filter(
        self,
        where_clause: WhereClause,
        params: SQLParamDict,
        user_id: Optional[UserIDT],
        object_mappings: TableMapping,
    ) -> None:
        """
            The generated SQL assumes that, in the query:
                'obh' is the alias for object_head aka ObjectHeader
                'obf' the alias for ObjectFields, if relevant to mapping system
                'acq' is the alias for Acquisition
                'sam' is the alias for Sample
        :param user_id: For filtering validators.
        :param where_clause: SQL filtering clauses on objects will be added there.
        :param params: SQL params will be added there.
        :param object_mappings: Free field mappings from project.
        :return:
        """

        # Hierarchy first
        if self.samples:
            samples_ids = [int(x) for x in self.samples.split(",")]
            where_clause *= "sam.sampleid = ANY (:samples)"
            params["samples"] = samples_ids

        if self.taxo:
            if self.taxo_child:
                # TODO: In this case a single taxon is allowed. Not very consistent
                where_clause *= (
                    "obh.classif_id IN ("
                    + TaxonomyBO.RQ_CHILDREN.replace(":ids", ":taxo")
                    + ")"
                )
                params["taxo"] = [int(self.taxo)]
            else:
                taxa = [int(x) for x in self.taxo.split(",") if x != "None"]
                if len(taxa) == 1:
                    where_clause *= "obh.classif_id = :taxo"
                    params["taxo"] = taxa[0]
                else:
                    where_clause *= "obh.classif_id = ANY (:taxo)"
                    params["taxo"] = taxa

        if self.status_filter:
            if self.status_filter == "NV":
                # Not Validated, better to enumerate the _other_ states
                cond = f"obh.classif_qual in ('{DUBIOUS_CLASSIF_QUAL}','{PREDICTED_CLASSIF_QUAL}')"
                if "taxo" not in params:
                    where_clause *= f"({cond} OR obh.classif_qual IS NULL)"
                else:  # classif_qual cannot be null if a category is present
                    # E.g. Not Validated Chaetognatha
                    where_clause *= cond
            elif self.status_filter == "PV":
                where_clause *= "obh.classif_qual IN ('%s','%s')" % (
                    VALIDATED_CLASSIF_QUAL,
                    PREDICTED_CLASSIF_QUAL,
                )
            elif self.status_filter == "NVM":
                where_clause *= "obh.classif_qual = '%s'" % VALIDATED_CLASSIF_QUAL
                where_clause *= "obh.classif_who != " + str(user_id)
            elif self.status_filter == "VM":
                where_clause *= "obh.classif_qual = '%s'" % VALIDATED_CLASSIF_QUAL
                where_clause *= "obh.classif_who = " + str(user_id)
            elif self.status_filter == "U":
                where_clause *= "obh.classif_qual IS NULL"
            elif self.status_filter == "UP":  # Updatable by Prediction
                where_clause *= (
                    "(obh.classif_qual = '%s' OR obh.classif_qual IS NULL)"
                    % PREDICTED_CLASSIF_QUAL
                )
            elif self.status_filter == "PVD":
                where_clause *= "obh.classif_qual IS NOT NULL"
            else:
                where_clause *= "obh.classif_qual = '" + self.status_filter[:3] + "'"

        if self.MapN and self.MapW and self.MapE and self.MapS:
            where_clause *= "obh.latitude BETWEEN :MapS AND :MapN"
            where_clause *= "obh.longitude BETWEEN :MapW AND :MapE"
            params["MapN"] = self.MapN
            params["MapW"] = self.MapW
            params["MapE"] = self.MapE
            params["MapS"] = self.MapS

        if self.depth_min and self.depth_max:
            where_clause *= "obh.depth_min BETWEEN :depthmin AND :depthmax"
            where_clause *= "obh.depth_max BETWEEN :depthmin AND :depthmax"
            params["depthmin"] = self.depth_min
            params["depthmax"] = self.depth_max

        if self.instrument:
            where_clause *= "prj.instrument_id ILIKE :instrum "
            params["instrum"] = "%" + self.instrument + "%"

        if self.daytime:
            where_clause *= "obh.sunpos = ANY (:daytime)"
            params["daytime"] = [x for x in self.daytime.split(",")]

        if self.months:
            where_clause *= "EXTRACT(month FROM obh.objdate) = ANY (:month)"
            params["month"] = [int(x) for x in self.months.split(",")]

        if self.from_date:
            where_clause *= "obh.objdate >= TO_DATE(:fromdate,'YYYY-MM-DD')"
            params["fromdate"] = self.from_date

        if self.to_date:
            where_clause *= "obh.objdate <= TO_DATE(:todate,'YYYY-MM-DD')"
            params["todate"] = self.to_date

        if self.invert_time:
            if self.from_time and self.to_time:
                where_clause *= (
                    "(obh.objtime <= time :fromtime OR obh.objtime >= time :totime)"
                )
                params["fromtime"] = self.from_time
                params["totime"] = self.to_time
        else:
            if self.from_time:
                where_clause *= "obh.objtime >= time :fromtime"
                params["fromtime"] = self.from_time
            if self.to_time:
                where_clause *= "obh.objtime <= time :totime"
                params["totime"] = self.to_time

        if self.validated_from:
            where_clause *= (  # TODO: not 100% accurate
                "obh.classif_date >= TO_TIMESTAMP(:validfromdate,'YYYY-MM-DD HH24:MI')"
            )
            params["validfromdate"] = self.validated_from

        if self.validated_to:
            where_clause *= (
                "obh.classif_date <= TO_TIMESTAMP(:validtodate,'YYYY-MM-DD HH24:MI')"
            )
            params["validtodate"] = self.validated_to

        if self.free_num and (
            self.free_num_start or self.free_num_end
        ):  # e.g. "on02" for object numeric Column #2 (1-based)
            if self.free_num_start:
                comp_op = " >= "
                bound = self.free_num_start
            else:
                assert self.free_num_end
                comp_op = " <= "
                bound = self.free_num_end
            try:
                criteria_col = "n%02d" % int(self.free_num[2:])
                is_split, real_col = object_mappings.phy_lookup(criteria_col)
                col_ref = ("obf" if is_split else "obh") + "." + real_col
                where_clause *= col_ref + comp_op + ":freenumbnd"
            except ValueError:
                # For some (probably) historical reason, Score is part of free_cols in UI
                # Assume it's the current prediction which is asked for
                criteria_col = self.COL_IN_FREE_NUM.get(self.free_num[1:], "?")
                where_clause *= "obh." + criteria_col + comp_op + ":freenumbnd"
            params["freenumbnd"] = bound

        if self.free_text and self.free_text_val:
            criteria_tbl = self.free_text[0]
            criteria_col = "t%02d" % int(self.free_text[2:])
            if criteria_tbl == "o":
                is_split, real_col = object_mappings.phy_lookup(criteria_col)
                col_ref = ("obf" if is_split else "obh") + "." + real_col
                where_clause *= col_ref + " ILIKE :freetxtval"
            elif criteria_tbl == "a":
                where_clause *= "acq." + criteria_col + " ILIKE :freetxtval"
            elif criteria_tbl == "s":
                where_clause *= "sam." + criteria_col + " ILIKE :freetxtval "
            elif criteria_tbl == "p":
                where_clause *= "prc." + criteria_col + " ILIKE :freetxtval "
            like_exp = "%" + self.free_text_val + "%"
            # Apply standard BOL/EOL regexp markers
            if like_exp[:2] == "%^":  # Exact match at beginning
                like_exp = like_exp[2:]
            if like_exp[-2:] == "$%":  # Exact match at end
                like_exp = like_exp[:-2]
            params["freetxtval"] = like_exp

        if self.annotators:
            where_clause *= (
                "(obh.classif_who = ANY (:filt_annot) OR ohu.in_annots IS NOT NULL)"
            )
            params["filt_annot"] = [int(x) for x in self.annotators.split(",")]
        elif self.last_annotators:
            where_clause *= "obh.classif_who = ANY (:filt_annot)"
            params["filt_annot"] = [int(x) for x in self.last_annotators.split(",")]

    def filters_without_taxo(self) -> ProjectFiltersDict:
        """
        Return a clone of self's filters, but removing any Taxonomy related condition.
        TODO: Some filtering of taxo is possible on free cols as well.
        """
        less_filtered = self.filters.copy()
        for a_key in self.TAXO_KEYS:
            less_filtered.pop(a_key, "")  # type:ignore
        return less_filtered


class DescribedObjectBOSet(object):
    """
    A (potentially large) set of objects, described by a base rule (all objects in projects XXX)
    and filtered by exclusion conditions.
    """

    __slots__ = ("project_ids", "user_id", "mapping", "filters")

    def __init__(
        self,
        session: Session,
        project_ids: ProjectIDListT,
        user_id: Optional[UserIDT],
        filters: ProjectFiltersDict,
    ):
        """
        :param user_id: The 'current' user, in case the filter refers to him/her.
        """
        self.project_ids = project_ids
        self.user_id = user_id
        object_mappings: TableMapping = TableMapping(
            ObjectFields, FREE_COLS_ARE_ELSEWHERE
        )
        sample_mappings: TableMapping = TableMapping(Sample)
        acquisition_mappings: TableMapping = TableMapping(Acquisition)
        process_mappings: TableMapping = TableMapping(Process)
        # store for iteration
        src_projects: List[Project] = (
            session.query(Project).filter(Project.projid.in_(self.project_ids)).all()
        )
        self.mapping: ProjectSetMapping = ProjectSetMapping().load_from_projects(
            src_projects
        )
        self.filters = ObjectSetFilter(session, filters)

    def get_sql(
        self,
        order_clause: Optional[OrderClause] = None,
        select_list: str = "",
        all_images: bool = False,
    ) -> Tuple[FromClause, WhereClause, SQLParamDict]:
        """
        Construct SQL parts for getting per-object information.
        :param order_clause: The required order by clause, possibly containing a resultset window.
        :param select_list: Used for hinting the builder that some specific table will be needed in join.
                major tables obj_head, samples and acquisitions are always joined.
        :param all_images: If not set (default), only return the lowest rank, i.e. visible, image
        :return:
        """
        if order_clause is None:
            order_clause = OrderClause()
        # The filters on objects
        obj_where = WhereClause()
        import json

        params: SQLParamDict = {
            "projid": ",".join([str(project_id) for project_id in self.project_ids])
        }

        self.filters.get_sql_filter(
            obj_where, params, self.user_id, self.mapping.object_mappings
        )
        column_referencing_sql = (
            select_list + obj_where.get_sql() + order_clause.get_sql()
        )
        selected_tables = FromClause(
            f"(select :projid as projid) prjs"
        )  # Prepare a future _set_ of projects
        if "prj." in column_referencing_sql:
            selected_tables += (
                f"{Project.__tablename__} prj ON prj.projid = prjs.projid"
            )
            selected_tables += f"{Sample.__tablename__} sam ON sam.projid = prj.projid"
        else:
            selected_tables += f"{Sample.__tablename__} sam ON sam.projid = prjs.projid"
        selected_tables += (
            f"{Acquisition.__tablename__} acq ON acq.acq_sample_id = sam.sampleid"
        )
        if "prc." in column_referencing_sql:
            selected_tables += (
                f"{Process.__tablename__} prc ON prc.processid = acq.acquisid"
            )
        obj_field_joined = "obf." in column_referencing_sql
        if obj_field_joined and self.driving_table_is_obj_field(
            obj_where.get_sql(),
            order_clause.get_sql(),
        ):
            selected_tables += (
                f"{ObjectFields.__tablename__} obf ON obf.acquis_id = acq.acquisid"
            )
            selected_tables += (
                f"{ObjectHeader.__tablename__} obh ON obh.objid = obf.objfid"
            )
        else:
            selected_tables += (
                f"{ObjectHeader.__tablename__} obh ON obh.acquisid = acq.acquisid"
            )
            if obj_field_joined:
                selected_tables += (
                    f"{ObjectFields.__tablename__} obf ON obf.objfid = obh.objid"
                )
        # if "prd." in column_referencing_sql:
        #     preds_ref = Prediction.__tablename__ + " prd"
        #     selected_tables += (
        #         preds_ref
        #         + " ON prd.object_id = obh.objid AND prd.classif_id = obh.classif_id"
        #     )
        #     if self.filters.status_filter not in MEANS_TRAINING_ID_EXIST:
        #         selected_tables.set_outer(preds_ref)
        # if "trn." in column_referencing_sql:
        #     trainings_ref = Training.__tablename__ + " trn"
        #     selected_tables += trainings_ref + " ON trn.training_id = prd.training_id"
        #     if self.filters.status_filter not in MEANS_TRAINING_ID_EXIST:
        #         selected_tables.set_outer(trainings_ref)
        if "ohu." in column_referencing_sql:  # Inline query for annotators in history
            selected_tables += (
                f"(select 1 as in_annots WHERE EXISTS (select * from {ObjectsClassifHisto.__tablename__} och "
                "WHERE och.objid = obh.objid AND och.classif_who = ANY (:filt_annot) ) ) ohu ON True"
            )
            selected_tables.set_outer("(select 1 as in_annots ")
            selected_tables.set_lateral("(select 1 as in_annots ")
        if "txo." in column_referencing_sql or "txp." in column_referencing_sql:
            selected_tables += (
                f"{Taxonomy.__tablename__} txo ON txo.id = obh.classif_id"
            )
            if (
                self.filters.status_filter not in MEANS_CLASSIF_ID_EXIST
                and not self.filters.taxo  # If some taxo is needed it's a plain join
            ):
                selected_tables.set_outer(f"{Taxonomy.__tablename__} txo ")
        if "img." in column_referencing_sql:
            selected_tables += (
                f"{Image.__tablename__} img ON obh.objid = img.objid "
                if all_images
                else f"(select * from {Image.__tablename__} img2 where obh.objid = img2.objid order by imgrank limit 1) img ON true"
            )
            selected_tables.set_lateral(f"(select * from {Image.__tablename__}")
        if "usr." in column_referencing_sql:
            selected_tables += f"{User.__tablename__} usr ON obh.classif_who = usr.id"
            selected_tables.set_outer(f"{User.__tablename__} usr ")
        if "txp." in column_referencing_sql:
            selected_tables += f"{Taxonomy.__tablename__} txp ON txp.id = txo.parent_id"
            selected_tables.set_outer(f"{Taxonomy.__tablename__} txp ")
        return selected_tables, obj_where, params

    def without_filtering_taxo(self):
        """
        Return a clone of self, but without any Taxonomy related filter.
        """
        filters_but_taxo = self.filters.filters_without_taxo()
        return DescribedObjectBOSet(
            self.filters.session, self.project_ids, self.user_id, filters_but_taxo
        )

    def driving_table_is_obj_field(self, where: str, order: str) -> bool:
        """Choose the fastest way to find needed objects.
        We mirror acquis_id from obj_head to obj_fields so 2 options are:
        -1 Fetch via acquis_id the big rows in obj_fields and then PK access to obj_head
        -2 Fetch via acquis_id the small rows in obj_head and then PK access to obj_fields
        1 is faster if we need the majority of rows, 2 is better if some filter eliminates based on obj_head cols.
        We don't know in advance the selectivity of filters, so there is kind of heuristic here.
        """
        ret = False
        if ("obf." in order) or ("obf." in where and "obh." not in where):
            ret = True
        if (
            "obh.classif_id" in where
        ):  # Very discriminating and covered by index 'is_objectsacqclassifqual'
            ret = False
        if (
            "obh.classif_qual" in where  # covered as well by 'is_objectsacqclassifqual'
            and self.filters.status_filter
            not in ("NV",)  # This OR-linked condition does not end up in index scan
        ):
            ret = False
        return ret

    def as_select_list(
        self, alias: str, table_name: str, mappingcols: Dict[str, str]
    ) -> str:
        """
        Return a SQL select list for given alias. col = name of db column mapping , name= name of tsv column
        """
        sels = []
        tsv_table_name = TABLE_TO_PREFIX[table_name]
        for name, col in mappingcols.items():
            sels.append('%s.%s AS "%s_%s"' % (alias, col, tsv_table_name, name))
        return ", " + ", ".join(sels) if sels else ""
