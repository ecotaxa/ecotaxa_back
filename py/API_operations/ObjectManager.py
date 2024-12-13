# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Tuple, List, Optional, Set, Any

from API_models.filters import ProjectFiltersDict
from API_models.prediction import PredictionInfoRsp
from BO.Classification import (
    HistoricalLastClassif,
    ClassifIDSetT,
    ClassifIDListT,
    ClassifIDT,
    ClassifScoresListT,
)
from BO.ColumnUpdate import ColUpdateList
from BO.Mappings import TableMapping
from BO.Object import ObjectBO
from BO.ObjectSet import (
    DescribedObjectSet,
    ObjectIDListT,
    EnumeratedObjectSet,
    ObjectIDWithParentsListT,
    ObjectSetFilter,
    ObjectSetClassifChangesT,
)
from BO.Project import ProjectBO, ChangeTypeT
from BO.ReClassifyLog import ReClassificationBO
from BO.Rights import RightsBO, Action
from BO.Taxonomy import TaxonomyBO, ClassifSetInfoT
from BO.Training import TrainingBO, PredictionBO
from BO.User import UserIDT
from DB.Image import IMAGE_VIRTUAL_COLUMNS
from DB.Object import (
    VALIDATED_CLASSIF_QUAL,
    PREDICTED_CLASSIF_QUAL,
    DUBIOUS_CLASSIF_QUAL,
    CLASSIF_QUALS,
    ObjectHeader,
)
from DB.Project import ProjectIDT, Project
from DB.helpers import Result
from DB.helpers.Direct import text
from DB.helpers.Postgres import db_server_now
from DB.helpers.SQL import OrderClause
from FS.VaultRemover import VaultRemover
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer
from .helpers.Service import Service

logger = get_logger(__name__)

# Basic hint preventing FTS on big tables
HINT = "/*+ IndexOnlyScan(obh) IndexOnlyScan(obf) */"


class ObjectManager(Service):
    """
    Object manager, read, update, delete...
    """

    # Delete this chunk of objects at a time
    CHUNK_SIZE = 400

    def __init__(self) -> None:
        super().__init__()

    def query(
        self,
        current_user_id: Optional[UserIDT],
        proj_id: ProjectIDT,
        filters: ProjectFiltersDict,
        return_fields: Optional[List[str]] = None,
        order_field: Optional[str] = None,
        window_start: Optional[int] = None,
        window_size: Optional[int] = None,
    ) -> Tuple[ObjectIDWithParentsListT, List[List[Any]], int]:
        """
        Query the given project with given filters, return all IDs.
        If provided order_field, the result is sorted by this field.
        Ambiguity is solved in a stable (over calls) way.
        window_start and window_size allow to select a window of data in the result.
        """
        # Security check
        if current_user_id is None:
            prj = RightsBO.anonymous_wants(self.ro_session, Action.READ, proj_id)
            # Anonymous can only see validated objects
            filters["statusfilter"] = "V"
            user_id = -1
        else:
            user, prj = RightsBO.user_wants(
                self.session, current_user_id, Action.READ, proj_id
            )
            user_id = user.id

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(
            self.ro_session, prj, user_id, filters
        )
        free_columns_mappings = object_set.mapping.object_mappings

        # The order fields have an impact on the query
        order_clause = self.cook_order_clause(
            order_field, free_columns_mappings, str(return_fields)
        )
        order_clause.set_window(window_start, window_size)

        extra_cols = self.add_return_fields(return_fields, free_columns_mappings)

        from_, where_clause, params = object_set.get_sql(order_clause, extra_cols)

        # Compute the total in a second step (_summarize)
        total_col = "0 AS total"

        sql = f"""
SELECT {HINT} obh.objid, acq.acquisid, sam.sampleid, %s%s
  FROM """ % (
            total_col,
            extra_cols,
        )
        sql += from_.get_sql() + " " + where_clause.get_sql()

        # Add order & window if relevant
        if order_clause is not None:
            sql += order_clause.get_sql()

        with CodeTimer("Query: SQL: %s PARAMS: %s: " % (sql, params), logger, 1):
            res: Result = self.ro_session.execute(text(sql), params)
        ids = []
        details = []
        total = 0
        objid: int
        acquisid: int
        sampleid: int
        to_apply = IMAGE_VIRTUAL_COLUMNS.get_transformers(res, offset_to_data=4)
        for objid, acquisid, sampleid, total, *extra in res:
            ids.append((objid, acquisid, sampleid, proj_id))
            [fct(extra) for fct in to_apply]
            details.append(extra)

        if total == 0:
            # Total was not computed, left to 0, execute again SQL from the same object set, but
            # without columns in select list, and no limit function.
            total, _nbr_v, _nbr_d, _nbr_p = self._summarize(
                object_set, proj_id=proj_id, only_total=True
            )

        # If we can, refresh the cache in background, most of the data should be in PG cache
        # if cache.should_refresh():
        #     # Try to fill the cache in background. We cannot pass a session as they do not cross threads.
        #     assert self.the_readonly_connection
        #     ObjectCacheWriter(cache).bg_fetch_fill(self.the_readonly_connection)

        return ids, details, total

    @staticmethod
    def cook_order_clause(
        order_field: Optional[str], mappings: TableMapping, return_fields_str: str
    ) -> OrderClause:
        """
        Prepare a SQL "order by" clause from the required field.
        The field is expressed using same table prefixes as return fields.
        """
        ret = OrderClause()
        if order_field is None:
            return ret
        asc_desc = None
        if order_field[0] == "-":
            asc_desc = "DESC"
            order_field = order_field[1:]
        order_expr = ObjectBO._field_to_db_col(order_field, mappings)
        if order_expr is None:
            return ret
        if " AS " in order_expr:
            alias = None
            order_expr, order_col = order_expr.split(" AS ")
            if (
                "." + order_col not in return_fields_str
            ):  # Uncommon but seen in logs: order by a not-displayed column
                order_col = order_expr
        else:
            alias, order_col = order_expr.split(".", 1)
        # From PG doc: If NULLS LAST is specified, null values sort after all non-null values;
        # if NULLS FIRST is specified, null values sort before all non-null values.
        # If neither is specified, the default behavior is NULLS LAST when ASC is specified or implied,
        #    and NULLS FIRST when DESC is specified
        #    ***(thus, the default is to act as though nulls are larger than non-nulls)***
        # From me (LS): This is utterly strange for dates, as it means that unknown is in the future.
        ret.add_expression(
            alias, order_col, asc_desc, invert_nulls_first="_when" in order_col
        )
        # Disambiguate using obj_id, from one object table or the other
        if alias == "obf":
            ret.add_expression("obf", "objfid", asc_desc)
        else:
            if "obh.objid" not in ret.referenced_columns():
                ret.add_expression("obh", "objid", asc_desc)
        return ret

    @classmethod
    def add_return_fields(
        cls, return_fields: Optional[List[str]], mapping: TableMapping
    ) -> str:
        """
            From an API-named list of columns, return the real text for the SELECT to return them
        :param return_fields: The fields in prefix+name convention
        :param mapping: Mapping to use
        :return:
        """
        vals = ObjectBO.resolve_fields(return_fields, mapping)
        if len(vals) == 0:
            return ""
        return ",\n" + ", ".join(vals)

    def get_prediction_infos(
        self, current_user_id: UserIDT, object_ids: ObjectIDListT
    ) -> PredictionInfoRsp:
        """
        Query the given IDs, return last prediction information.
        """
        # Security check
        obj_set = EnumeratedObjectSet(self.ro_session, object_ids)
        # Get project IDs for the objects and verify rights
        prj_ids = obj_set.get_projects_ids()
        for a_prj_id in prj_ids:
            RightsBO.user_wants(self.session, current_user_id, Action.READ, a_prj_id)
        infos = PredictionBO(self.session, obj_set.object_ids).get_prediction_infos()
        return PredictionInfoRsp(result=infos)

    def parents_by_id(
        self, current_user_id: UserIDT, object_ids: ObjectIDListT
    ) -> ObjectIDWithParentsListT:
        """
        Query the given IDs, return parents.
        """
        # Security check
        obj_set = EnumeratedObjectSet(self.ro_session, object_ids)
        # Get project IDs for the objects and verify rights
        prj_ids = obj_set.get_projects_ids()
        for a_prj_id in prj_ids:
            RightsBO.user_wants(self.session, current_user_id, Action.READ, a_prj_id)

        sql = (
            """
    SELECT obh.objid, acq.acquisid, sam.sampleid, sam.projid
      FROM %s obh
      JOIN acquisitions acq on acq.acquisid = obh.acquisid 
      JOIN samples sam on sam.sampleid = acq.acq_sample_id 
     WHERE obh.objid = any (:ids) """
            % ObjectHeader.__tablename__
        )
        params = {"ids": object_ids}

        res: Result = self.ro_session.execute(text(sql), params)
        ids = [
            (objid, acquisid, sampleid, projid)
            for objid, acquisid, sampleid, projid in res
        ]
        return ids

    def summary(
        self,
        current_user_id: Optional[UserIDT],
        proj_id: ProjectIDT,
        filters: ProjectFiltersDict,
        only_total: bool,
    ) -> Tuple[int, Optional[int], Optional[int], Optional[int]]:
        """
        Query the given project with given filters, return classification summary, or just grand total if
        only_total is set.
        """
        # Security check
        prj: Project
        if current_user_id is None:
            prj = RightsBO.anonymous_wants(self.session, Action.READ, proj_id)
            # Anonymous can only see validated objects
            # TODO: Dup code
            # noinspection PyTypeHints
            filters["statusfilter"] = "V"
            user_id = -1
        else:
            user, prj = RightsBO.user_wants(
                self.session, current_user_id, Action.READ, proj_id
            )
            user_id = user.id

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(
            self.ro_session, prj, user_id, filters
        )
        return self._summarize(object_set, proj_id, only_total)

    def _summarize(
        self, object_set: DescribedObjectSet, proj_id: ProjectIDT, only_total: bool
    ):
        """
        Compute the summary of given object_set
        """
        from_, where, params = object_set.get_sql()
        sql = f"""
SELECT {HINT} COUNT(*) nbr"""
        if only_total:
            sql += """, NULL nbr_v, NULL nbr_d, NULL nbr_p"""
        else:
            sql += f""",
            COUNT(*) FILTER (WHERE obh.classif_qual = '{VALIDATED_CLASSIF_QUAL}') nbr_v,
            COUNT(*) FILTER (WHERE obh.classif_qual = '{DUBIOUS_CLASSIF_QUAL}') nbr_d,
            COUNT(*) FILTER (WHERE obh.classif_qual = '{PREDICTED_CLASSIF_QUAL}') nbr_p"""
        sql += (
            """
      FROM """
            + from_.get_sql()
            + " "
            + where.get_sql()
        )
        with CodeTimer(
            "summary: V/D/P for %d SQL %s PARAMS %s " % (proj_id, sql, params),
            logger,
            0.3,
        ):
            res: Result = self.ro_session.execute(text(sql), params)
        nbr: int
        nbr_v: Optional[int]
        nbr_d: Optional[int]
        nbr_p: Optional[int]
        nbr, nbr_v, nbr_d, nbr_p = res.first()  # type:ignore
        return nbr, nbr_v, nbr_d, nbr_p

    def delete(
        self, current_user_id: UserIDT, object_ids: ObjectIDListT
    ) -> Tuple[int, int, int, int]:
        """
        Remove from DB all the objects with ID in given list.
        """
        # Security check
        obj_set = EnumeratedObjectSet(self.session, object_ids)
        # Get project IDs for the objects and verify rights
        prj_ids = obj_set.get_projects_ids()
        for a_prj_id in prj_ids:
            RightsBO.user_wants(
                self.session, current_user_id, Action.ADMINISTRATE, a_prj_id
            )

        # Prepare & start a remover thread that will run in // with DB queries
        remover = VaultRemover(self.config, logger).do_start()
        # Do the deletion itself.
        nb_objs, nb_img_rows, img_files = obj_set.delete(
            self.CHUNK_SIZE, remover.add_files
        )

        # Update stats on impacted project(s)
        for prj_id in prj_ids:
            ProjectBO.update_taxo_stats(self.session, prj_id)
            # Stats depend on taxo stats
            ProjectBO.update_stats(self.session, prj_id)

        self.session.commit()
        # Wait for the files handled
        remover.wait_for_done()
        return nb_objs, 0, nb_img_rows, len(img_files)

    def force_to_predicted(
        self, current_user_id: UserIDT, proj_id: ProjectIDT, filters: ProjectFiltersDict
    ) -> None:
        """
        Query the given project with given filters, force the resulting objects to Predicted with their
        current classification and a conventional score.
        """
        # Security check
        _user, project = RightsBO.user_wants(
            self.session, current_user_id, Action.ADMINISTRATE, proj_id
        )

        impacted_objs = [r[0] for r in self.query(current_user_id, proj_id, filters)[0]]

        training = TrainingBO.create_one(
            self.session, current_user_id, f"Force to P in {proj_id}"
        )
        nb_upd, all_changes = EnumeratedObjectSet(
            self.session, impacted_objs
        ).force_to_predicted(training)

        # Propagate changes to update projects_taxo_stat
        self.propagate_classif_changes(nb_upd, all_changes, project)

        # Update stats
        ProjectBO.update_taxo_stats(self.session, proj_id)
        # Stats depend on taxo stats
        ProjectBO.update_stats(self.session, proj_id)
        self.session.commit()

    def _the_project_for(
        self, current_user_id: UserIDT, target_ids: ObjectIDListT, action: Action
    ) -> Tuple[EnumeratedObjectSet, Project]:
        """
        Check _the_ single project for an object set, with the given right.
        """
        # Get project IDs for the objects and verify rights
        object_set = EnumeratedObjectSet(self.session, target_ids)
        prj_ids = object_set.get_projects_ids()
        # All should be in same project, so far
        assert len(prj_ids) == 1, "Too many or no projects for objects: %s" % target_ids
        prj_id = prj_ids[0]
        _user, project = RightsBO.user_wants(
            self.session, current_user_id, action, prj_id
        )
        assert project  # for mypy
        return object_set, project

    def update_set(
        self,
        current_user_id: UserIDT,
        target_ids: ObjectIDListT,
        updates: ColUpdateList,
    ) -> int:
        """
        Update the given set, using provided updates.
        """
        object_set, project = self._the_project_for(
            current_user_id, target_ids, Action.ADMINISTRATE
        )
        return object_set.apply_on_all(project, updates)

    def revert_to_history(
        self,
        current_user_id: UserIDT,
        proj_id: ProjectIDT,
        filters: ProjectFiltersDict,
        dry_run: bool,
        target: Optional[int],
    ) -> Tuple[List[HistoricalLastClassif], ClassifSetInfoT]:
        """
        Revert to classification history the given set, if dry_run then only simulate.
        """
        # Security check
        RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, proj_id)

        # Get target objects
        impacted_objs = [r[0] for r in self.query(current_user_id, proj_id, filters)[0]]
        obj_set = EnumeratedObjectSet(self.session, impacted_objs)

        # We don't revert to a previous version in history from same annotator
        but_not_by: Optional[int] = None
        but_not_by_str = filters.get("filt_last_annot", None)
        if but_not_by_str is not None:
            try:
                but_not_by = int(but_not_by_str)
            except ValueError:
                pass
        if dry_run:
            # Return information on what to do
            impact = obj_set.evaluate_revert_to_history(target, but_not_by)
            # And names for display
            classifs = TaxonomyBO.names_with_parent_for(
                self.session, self.collect_classif(impact)
            )
        else:
            # Do the real thing
            impact = obj_set.revert_to_history(target, but_not_by)
            classifs = {}
            # Update stats
            ProjectBO.update_taxo_stats(self.session, proj_id)
            # Stats depend on taxo stats
            ProjectBO.update_stats(self.session, proj_id)
            self.session.commit()
        # Give feedback
        return impact, classifs

    def reclassify(
        self,
        current_user_id: UserIDT,
        proj_id: ProjectIDT,
        filters: ProjectFiltersDict,
        forced_id: ClassifIDT,
        reason: str,
    ) -> int:
        """
        Regardless of present classification or state, set the new classification for this object set.
        This can be used to, e.g. move to another taxonomy system.
        """
        # Security check
        user, project = RightsBO.user_wants(
            self.session, current_user_id, Action.ANNOTATE, proj_id
        )

        # Determine if it's the use case 'global search & replace a single category with another'
        filter_set = ObjectSetFilter(self.ro_session, filters)
        only_taxon = filter_set.category_id_only()

        # Get target objects
        impacted_objs = [r[0] for r in self.query(current_user_id, proj_id, filters)[0]]
        obj_set = EnumeratedObjectSet(self.session, impacted_objs)

        # Do the raw classification with history.
        classif_ids = [forced_id] * len(obj_set.object_ids)
        now = db_server_now(self.session)
        nb_upd, all_changes = obj_set.classify_validate(
            current_user_id, classif_ids, "=", now
        )

        if only_taxon is not None:
            ReClassificationBO.add_log(
                self.session, only_taxon, forced_id, proj_id, reason, nb_upd, now
            )

        # Propagate changes to update projects_taxo_stat and commit
        self.propagate_classif_changes(nb_upd, all_changes, project)

        return len(obj_set)

    @staticmethod
    def collect_classif(histo: List[HistoricalLastClassif]) -> ClassifIDSetT:
        """
        Collect classification IDs from given list, for lookup & display.
        """
        ret: Set[Optional[ClassifIDT]] = set()
        for an_histo in histo:
            ret.add(an_histo.classif_id)
            ret.add(an_histo.histo_classif_id)
        # Eventually remove the None
        if None in ret:
            ret.remove(None)
        return ret  # type:ignore # mypy doesn't spot the None removal above

    def classify_set(
        self,
        current_user_id: UserIDT,
        target_ids: ObjectIDListT,
        classif_ids: ClassifIDListT,
        wanted_qualif: str,
    ) -> Tuple[int, int, ObjectSetClassifChangesT]:
        """
        Classify (mostly from human source) or validate/set to dubious a set of objects.
        """
        # Get the objects and project, checking rights at the same time.
        object_set, project = self._the_project_for(
            current_user_id, target_ids, Action.ANNOTATE
        )
        # Do the raw classification with history.
        now = db_server_now(self.session)
        nb_upd, all_changes = object_set.classify_validate(
            current_user_id, classif_ids, wanted_qualif, now
        )
        # Propagate changes to update projects_taxo_stat
        self.propagate_classif_changes(nb_upd, all_changes, project)
        # Return status
        return nb_upd, project.projid, all_changes

    def classify_auto_mult_set(
        self,
        current_user_id: UserIDT,
        training: Optional[TrainingBO],
        target_ids: ObjectIDListT,
        classif_ids: List[ClassifIDListT],
        scores: List[ClassifScoresListT],
    ) -> Tuple[int, int, ObjectSetClassifChangesT]:
        """
        Classify (from automatic source) a set of objects.
        """
        # Get the objects and project, checking rights at the same time.
        object_set, project = self._the_project_for(
            current_user_id, target_ids, Action.ANNOTATE
        )
        # Create a new training if not set (always, so far)
        if training is None:
            training = TrainingBO.create_one(
                self.session, current_user_id, f"Classify auto in {project.projid}"
            )
        # Do the raw classification, eventually with history.
        nb_upd, all_changes = object_set.classify_auto_mult(
            training, classif_ids, scores
        )
        # Propagate changes to update projects_taxo_stat
        self.propagate_classif_changes(nb_upd, all_changes, project)
        # Return status
        return nb_upd, project.projid, all_changes

    def propagate_classif_changes(
        self, nb_upd: int, all_changes: ObjectSetClassifChangesT, project: Project
    ) -> None:
        """After a classification, update stats"""
        if nb_upd > 0:
            # Log a bit
            for a_chg, impacted in all_changes.items():
                logger.info("change %s for %s", a_chg, impacted)
            # Collate changes
            collated_changes: ChangeTypeT = {}
            for (
                prev_classif_id,
                prev_classif_qual,
                new_classif_id,
                wanted_qualif,
            ), objects in all_changes.items():
                # Decrement for what was before
                self.count_in_and_out(
                    collated_changes, prev_classif_id, prev_classif_qual, -len(objects)
                )
                # Increment for what arrives
                self.count_in_and_out(
                    collated_changes, new_classif_id, wanted_qualif, len(objects)
                )
            # Update the table
            ProjectBO.incremental_update_taxo_stats(
                self.session, project.projid, collated_changes
            )
            self.session.commit()
        else:
            self.session.rollback()

    @staticmethod
    def count_in_and_out(
        cumulated_changes: ChangeTypeT,
        classif_id: Optional[ClassifIDT],
        qualif: str,
        inc_or_dec: int,
    ) -> None:
        """Cumulate change +/- for a given taxon"""
        if classif_id is None:
            classif_id = -1  # Unclassified
        changes_for_id = cumulated_changes.setdefault(
            classif_id,
            {
                "n": 0,
                VALIDATED_CLASSIF_QUAL: 0,
                PREDICTED_CLASSIF_QUAL: 0,
                DUBIOUS_CLASSIF_QUAL: 0,
            },
        )
        changes_for_id["n"] += inc_or_dec
        if qualif in CLASSIF_QUALS:
            changes_for_id[qualif] += inc_or_dec
