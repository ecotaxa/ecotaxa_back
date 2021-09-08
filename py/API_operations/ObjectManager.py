# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Tuple, List, Optional, Set, Dict

from API_models.crud import ProjectFilters
from BO.Classification import HistoricalLastClassif, ClassifIDSetT, ClassifIDListT, ClassifIDT
from BO.ColumnUpdate import ColUpdateList
from BO.Mappings import TableMapping
from BO.ObjectSet import DescribedObjectSet, ObjectIDListT, EnumeratedObjectSet, ObjectIDWithParentsListT, \
    ObjectSetFilter
from BO.Project import ProjectBO
from BO.ReClassifyLog import ReClassificationBO
from BO.Rights import RightsBO, Action
from BO.Taxonomy import TaxonomyBO, ClassifSetInfoT
from BO.User import UserIDT
from DB import Project, ObjectHeader, ObjectFields, Image, Taxonomy, Sample, User
from DB.Project import ProjectIDT
from DB.helpers.Direct import text
from DB.helpers.ORM import Result
from DB.helpers.SQL import OrderClause
from FS.VaultRemover import VaultRemover
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer
from .helpers.Service import Service

logger = get_logger(__name__)


class ObjectManager(Service):
    """
        Object manager, read, update, delete...
    """
    # Delete this chunk of objects at a time
    CHUNK_SIZE = 400

    def __init__(self):
        super().__init__()

    def query(self, current_user_id: Optional[UserIDT], proj_id: ProjectIDT,
              filters: ProjectFilters,
              return_fields: Optional[List[str]] = None,
              order_field: Optional[str] = None,
              window_start: Optional[int] = None,
              window_size: Optional[int] = None) \
            -> Tuple[ObjectIDWithParentsListT, List[List], int]:
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
            # noinspection PyTypeHints
            filters.statusfilter = "V"  # type:ignore
            user_id = -1
        else:
            user, prj = RightsBO.user_wants(self.session, current_user_id, Action.READ, proj_id)
            user_id = user.id

        free_columns_mappings = TableMapping(ObjectFields).load_from_equal_list(prj.mappingobj)

        # The order field has an impact on the query
        order_clause = self.cook_order_clause(order_field, free_columns_mappings)

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(self.ro_session, proj_id, filters)

        extra_cols = self._add_return_fields(return_fields, free_columns_mappings)

        from_, where_clause, params = object_set.get_sql(user_id, order_clause, extra_cols)

        oid_lst, cnt = None, None
        # with ObjectCache(project=prj, mapping=free_columns_mappings,
        #                  where_clause=where_clause, order_clause=order_clause, params=params,
        #                  window_start=window_start, window_size=window_size) as cache:
        #     oid_lst, cnt = cache.pump_cache()

        if oid_lst is not None:
            total_col = "%d AS total" % cnt
        elif "obf." in where_clause.get_sql():
            # If the filter needs obj_field data it's more efficient to count with a window function
            # than issuing a second query.
            total_col = "COUNT(obh.objid) OVER() AS total"
        else:
            # Otherwise, no need for obj_field in count, less DB buffers
            total_col = "0 AS total"

        # The following hint is needed until we sort out why, time to time, there is a FTS on obj_head
        sql = """
    SET LOCAL enable_seqscan=FALSE;"""
        if oid_lst is not None:
            if len(oid_lst) == 0:  # All was filtered but an empty array does not work in below query
                oid_lst = [-1]  # impossible objid
            # SqlDialectInspection,SqlResolve
            sql += "\n    WITH ordr (ordr, objid)"
            sql += " AS (select * from UNNEST(:numbrs, :oids)) "
            # The CTE is ordered and in practice it orders the result as well,
            # but let's not depend on it, in case PG behavior evolves.
            params["numbrs"] = list(range(len(oid_lst)))
            params["oids"] = oid_lst
            from_ += "ordr ON ordr.objid = obh.objid"
            order_clause = OrderClause()
            order_clause.add_expression("ordr", "ordr")
            window_start = window_size = None  # The window is in the CTE
        sql += """
    SELECT obh.objid, acq.acquisid, sam.sampleid, %s%s
      FROM """ % (total_col, extra_cols)
        sql += from_.get_sql() + " " + where_clause.get_sql()

        # Add order & window if relevant
        if order_clause is not None:
            sql += order_clause.get_sql()
        if window_start is not None:
            sql += " OFFSET %d" % window_start
        if window_size is not None:
            sql += " LIMIT %d" % window_size

        with CodeTimer("query: for %d using %s " % (proj_id, sql), logger):
            res: Result = self.ro_session.execute(text(sql), params)
        ids = []
        details = []
        total = 0
        objid: int
        acquisid: int
        sampleid: int
        for objid, acquisid, sampleid, total, *extra in res:  # type:ignore
            ids.append((objid, acquisid, sampleid, proj_id))
            details.append(extra)

        if total == 0:
            # Total was not computed or left to 0
            total, _nbr_v, _nbr_d, _nbr_p = self.summary(current_user_id, proj_id, filters, only_total=True)

        # If we can, refresh the cache in background, most of the data should be in PG cache
        # if cache.should_refresh():
        #     # Try to fill the cache in background. We cannot pass a session as they do not cross threads.
        #     assert self.the_readonly_connection
        #     ObjectCacheWriter(cache).bg_fetch_fill(self.the_readonly_connection)

        return ids, details, total

    @staticmethod
    def cook_order_clause(order_field: Optional[str], mappings: TableMapping) -> Optional[OrderClause]:
        """
            Prepare a SQL "order by" clause from the required field.
            The field is expressed using same table prefixes as return fields.
        """
        if order_field is None:
            return None
        ret = OrderClause()
        asc_desc = None
        if order_field[0] == "-":
            asc_desc = "DESC"
            order_field = order_field[1:]
        order_expr = ObjectManager._field_to_db_col(order_field, mappings)
        if order_expr is None:
            return None
        alias, order_col = order_expr.split(".", 1)
        ret.add_expression(alias, order_col, asc_desc)
        # Disambiguate using obj_id, from one object table or the other
        if alias == "obf":
            ret.add_expression("obf", "objfid", asc_desc)
        else:
            ret.add_expression("obh", "objid", asc_desc)
        return ret

    @staticmethod
    def _field_to_db_col(a_field: str, mappings: TableMapping) -> Optional[str]:
        try:
            prfx, name = a_field.split(".", 1)
        except ValueError:
            return None
        if prfx == "obj":
            if name in ObjectHeader.__dict__:
                return "obh." + name
            elif name == 'imgcount':
                return "(SELECT COUNT(img2.imgrank) FROM images img2 WHERE img2.objid = obh.objid) AS imgcount"
        elif prfx == "fre":
            if name in mappings.tsv_cols_to_real:
                return "obf." + mappings.tsv_cols_to_real[name]
        elif prfx == "img":
            if name in Image.__dict__:
                return a_field
        elif prfx in ("txo", "txp"):
            if name in Taxonomy.__dict__:
                return a_field
        elif prfx == "sam":
            if name in Sample.__dict__:
                return a_field
        elif prfx == "usr":
            if name in User.__dict__:
                return a_field
        return None

    @staticmethod
    def _add_return_fields(return_fields: Optional[List[str]],
                           mappings: TableMapping) -> str:
        """
            From an API-named list of columns, return the real text for the SELECT to return them
        :param return_fields:
        :return:
        """
        if return_fields is None or len(return_fields) == 0:
            return ""
        vals = []
        for a_field in return_fields:
            a_col = ObjectManager._field_to_db_col(a_field, mappings)
            if a_col is None:
                logger.warning("Dropped unknown %s in query", a_field)
                continue
            vals.append(a_col)
        return ",\n" + ", ".join(vals)

    def parents_by_id(self, current_user_id: UserIDT, object_ids: ObjectIDListT) -> ObjectIDWithParentsListT:
        """
            Query the given IDs, return parents.
        """
        # Security check
        obj_set = EnumeratedObjectSet(self.ro_session, object_ids)
        # Get project IDs for the objects and verify rights
        prj_ids = obj_set.get_projects_ids()
        for a_prj_id in prj_ids:
            RightsBO.user_wants(self.session, current_user_id, Action.READ, a_prj_id)

        sql = """
    SELECT obh.objid, acq.acquisid, sam.sampleid, sam.projid
      FROM obj_head obh
      JOIN acquisitions acq on acq.acquisid = obh.acquisid 
      JOIN samples sam on sam.sampleid = acq.acq_sample_id 
     WHERE obh.objid = any (:ids) """
        params = {"ids": object_ids}

        res: Result = self.ro_session.execute(text(sql), params)
        ids = [(objid, acquisid, sampleid, projid)
               for objid, acquisid, sampleid, projid in res]
        return ids  # type:ignore

    def summary(self, current_user_id: Optional[UserIDT], proj_id: ProjectIDT, filters: ProjectFilters,
                only_total: bool) -> Tuple[int, Optional[int], Optional[int], Optional[int]]:
        """
            Query the given project with given filters, return classification summary, or just grand total if
            only_total is set.
        """
        # Security check
        if current_user_id is None:
            RightsBO.anonymous_wants(self.session, Action.READ, proj_id)
            # Anonymous can only see validated objects
            # TODO: Dup code
            # noinspection PyTypeHints
            filters.statusfilter = "V"  # type:ignore
            user_id = -1
        else:
            user, _project = RightsBO.user_wants(self.session, current_user_id, Action.READ, proj_id)
            user_id = user.id

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(self.ro_session, proj_id, filters)
        from_, where, params = object_set.get_sql(user_id)
        sql = """
    SET LOCAL enable_seqscan=FALSE;
    SELECT COUNT(*) nbr"""
        if only_total:
            sql += """, NULL nbr_v, NULL nbr_d, NULL nbr_p"""
        else:
            sql += """, 
           COUNT(CASE WHEN obh.classif_qual = 'V' THEN 1 END) nbr_v,
           COUNT(CASE WHEN obh.classif_qual = 'D' THEN 1 END) nbr_d, 
           COUNT(CASE WHEN obh.classif_qual = 'P' THEN 1 END) nbr_p"""
        sql += """
      FROM """ + from_.get_sql() + " " + where.get_sql()

        with CodeTimer("summary: V/D/P for %d using %s " % (proj_id, sql), logger):
            res: Result = self.ro_session.execute(text(sql), params)

        nbr: int
        nbr_v: Optional[int]
        nbr_d: Optional[int]
        nbr_p: Optional[int]
        nbr, nbr_v, nbr_d, nbr_p = res.first()  # type:ignore
        return nbr, nbr_v, nbr_d, nbr_p

    def delete(self, current_user_id: UserIDT, object_ids: ObjectIDListT) -> Tuple[int, int, int, int]:
        """
            Remove from DB all the objects with ID in given list.
        """
        # Security check
        obj_set = EnumeratedObjectSet(self.session, object_ids)
        # Get project IDs for the objects and verify rights
        prj_ids = obj_set.get_projects_ids()
        for a_prj_id in prj_ids:
            RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, a_prj_id)

        # Prepare & start a remover thread that will run in // with DB queries
        remover = VaultRemover(self.link_src, logger).do_start()
        # Do the deletion itself.
        nb_objs, nb_img_rows, img_files = obj_set.delete(self.CHUNK_SIZE, remover.add_files)

        # Update stats on impacted project(s)
        for prj_id in prj_ids:
            ProjectBO.update_taxo_stats(self.session, prj_id)
            # Stats depend on taxo stats
            ProjectBO.update_stats(self.session, prj_id)

        self.session.commit()
        # Wait for the files handled
        remover.wait_for_done()
        return nb_objs, 0, nb_img_rows, len(img_files)

    def reset_to_predicted(self, current_user_id: UserIDT, proj_id: ProjectIDT, filters: ProjectFilters) -> None:
        """
            Query the given project with given filters, reset the resulting objects to predicted.
        """
        # Security check
        RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, proj_id)

        impacted_objs = [r[0] for r in self.query(current_user_id, proj_id, filters)[0]]

        EnumeratedObjectSet(self.session, impacted_objs).reset_to_predicted()

        # Update stats
        ProjectBO.update_taxo_stats(self.session, proj_id)
        # Stats depend on taxo stats
        ProjectBO.update_stats(self.session, proj_id)
        self.session.commit()

    def _the_project_for(self, current_user_id: UserIDT, target_ids: ObjectIDListT, action: Action) \
            -> Tuple[EnumeratedObjectSet, Project]:
        """
            Check _the_ single project for an object set, with the given right.
        """
        # Get project IDs for the objects and verify rights
        object_set = EnumeratedObjectSet(self.session, target_ids)
        prj_ids = object_set.get_projects_ids()
        # All should be in same project, so far
        assert len(prj_ids) == 1, "Too many or no projects for objects: %s" % target_ids
        prj_id = prj_ids[0]
        _user, project = RightsBO.user_wants(self.session, current_user_id, action, prj_id)
        assert project  # for mypy
        return object_set, project

    def update_set(self, current_user_id: UserIDT, target_ids: ObjectIDListT, updates: ColUpdateList) -> int:
        """
            Update the given set, using provided updates.
        """
        object_set, project = self._the_project_for(current_user_id, target_ids, Action.ADMINISTRATE)
        return object_set.apply_on_all(project, updates)

    def revert_to_history(self, current_user_id: UserIDT, proj_id: ProjectIDT,
                          filters: ProjectFilters, dry_run: bool,
                          target: Optional[int]) -> Tuple[List[HistoricalLastClassif], ClassifSetInfoT]:
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
        but_not_by_str = filters.get('filt_last_annot', None)
        if but_not_by_str is not None:
            try:
                but_not_by = int(but_not_by_str)
            except ValueError:
                pass
        if dry_run:
            # Return information on what to do
            impact = obj_set.evaluate_revert_to_history(target, but_not_by)
            # And names for display
            classifs = TaxonomyBO.names_with_parent_for(self.session, self.collect_classif(impact))
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

    def reclassify(self, current_user_id: UserIDT, proj_id: ProjectIDT,
                   filters: ProjectFilters, forced_id: ClassifIDT, reason: str) -> int:
        """
            Regardless of present classification or state, set the new classification for this object set.
        """
        # Security check
        user, project = RightsBO.user_wants(self.session, current_user_id, Action.ANNOTATE, proj_id)

        # Get target objects
        impacted_objs = [r[0] for r in self.query(current_user_id, proj_id, filters)[0]]
        obj_set = EnumeratedObjectSet(self.session, impacted_objs)

        # Do the raw classification with history.
        classif_ids = [forced_id for _an_obj in obj_set.object_ids]
        nb_upd, all_changes = obj_set.classify_validate(current_user_id, classif_ids, "=")
        # Propagate changes to update projects_taxo_stat
        self.propagate_classif_changes(nb_upd, all_changes, project)

        # If filter was _only_ a single category, then write a log line
        filter_set = ObjectSetFilter(self.ro_session, filters)
        only_taxon = filter_set.category_id_only()
        if only_taxon is not None:
            ReClassificationBO.add_log(self.session, only_taxon, forced_id, proj_id, reason, nb_upd)

        self.session.commit()

        return len(obj_set)

    @staticmethod
    def collect_classif(histo: List[HistoricalLastClassif]) -> ClassifIDSetT:
        """
            Collect classification IDs from given list, for lookup & display.
        """
        ret: Set = set()
        for an_histo in histo:
            ret.add(an_histo.classif_id)
            ret.add(an_histo.histo_classif_id)
        # Eventually remove the None
        if None in ret:
            ret.remove(None)
        return ret

    def classify_set(self, current_user_id: UserIDT,
                     target_ids: ObjectIDListT, classif_ids: ClassifIDListT,
                     wanted_qualif: str) -> Tuple[int, int, Dict]:
        """
            Classify (from human source) or validate/set to dubious a set of objects.
        """
        # Get the objects and project, checking rights at the same time.
        object_set, project = self._the_project_for(current_user_id, target_ids, Action.ANNOTATE)
        # Do the raw classification with history.
        nb_upd, all_changes = object_set.classify_validate(current_user_id, classif_ids, wanted_qualif)
        # Propagate changes to update projects_taxo_stat
        self.propagate_classif_changes(nb_upd, all_changes, project)
        # Return status
        return nb_upd, project.projid, all_changes

    def classify_auto_set(self, current_user_id: UserIDT,
                          target_ids: ObjectIDListT, classif_ids: ClassifIDListT, scores: List[float],
                          keep_logs: bool) -> Tuple[int, int, Dict]:
        """
            Classify (from automatic source) a set of objects.
        """
        # Get the objects and project, checking rights at the same time.
        object_set, project = self._the_project_for(current_user_id, target_ids, Action.ANNOTATE)
        # Do the raw classification, eventually with history.
        nb_upd, all_changes = object_set.classify_auto(classif_ids, scores, keep_logs)
        # Propagate changes to update projects_taxo_stat
        self.propagate_classif_changes(nb_upd, all_changes, project)
        # Return status
        return nb_upd, project.projid, all_changes

    def propagate_classif_changes(self, nb_upd: int, all_changes: Dict[Tuple, ObjectIDListT],
                                  project: Project):
        """ After a classification, update stats """
        if nb_upd > 0:
            # Log a bit
            for a_chg, impacted in all_changes.items():
                logger.info("change %s for %s", a_chg, impacted)
            # Collate changes
            collated_changes: Dict[int, Dict] = {}
            for (prev_classif_id, prev_classif_qual, new_classif_id, wanted_qualif), objects in all_changes.items():
                # Decrement for what was before
                self.count_in_and_out(collated_changes, prev_classif_id, prev_classif_qual, -len(objects))
                # Increment for what arrives
                self.count_in_and_out(collated_changes, new_classif_id, wanted_qualif, len(objects))
            # Update the table
            ProjectBO.incremental_update_taxo_stats(self.session, project.projid, collated_changes)
            self.session.commit()
        else:
            self.session.rollback()

    @staticmethod
    def count_in_and_out(cumulated_changes, classif_id, qualif, inc_or_dec):
        """ Cumulate change +/- for a given taxon """
        if classif_id is None:
            classif_id = -1  # Unclassified
        changes_for_id = cumulated_changes.setdefault(classif_id, {'n': 0, 'V': 0, 'P': 0, 'D': 0})
        changes_for_id['n'] += inc_or_dec
        if qualif in ('V', 'P', 'D'):
            changes_for_id[qualif] += inc_or_dec
