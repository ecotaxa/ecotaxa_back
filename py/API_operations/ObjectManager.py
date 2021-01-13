# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Tuple, List, Optional, Set, Dict

from API_models.crud import ProjectFilters, ColUpdateList
from BO.Classification import HistoricalLastClassif, ClassifIDSetT, ClassifIDListT
from BO.ObjectSet import DescribedObjectSet, ObjectIDListT, EnumeratedObjectSet, ObjectIDWithParentsListT
from BO.Project import ProjectBO, ProjectIDT
from BO.Rights import RightsBO, Action
from BO.Taxonomy import TaxonomyBO, ClassifSetInfoT
from BO.User import UserIDT
from DB import Project, ObjectHeader
from DB.helpers.ORM import ResultProxy
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
              order_field: Optional[str] = None,
              window_start: Optional[int] = None,
              window_size: Optional[int] = None) \
            -> Tuple[ObjectIDWithParentsListT, int]:
        """
            Query the given project with given filters, return all IDs.
            If provided order_field, the result is sorted by this field.
            Ambiguity is solved in a stable (over calls) way.
            window_start and window_size allow to select a window of data in the result.
        """
        # Security check
        if current_user_id is None:
            RightsBO.anonymous_wants(self.session, Action.READ, proj_id)
            # Anonymous can only see validated objects
            # noinspection PyTypeHints
            filters.statusfilter = "V"  # type:ignore
            user_id = -1
        else:
            user, _project = RightsBO.user_wants(self.session, current_user_id, Action.READ, proj_id)
            user_id = user.id

        # The order field has an impact on the query
        order_clause = self.cook_order_clause(order_field)

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(self.session, proj_id, filters)

        from_, where, params = object_set.get_sql(user_id, order_clause)

        if "obf." in where.get_sql():
            # If the filter needs obj_field data it's more efficient to count with a window function
            # than issuing a second query.
            extra_col = ", COUNT(objid) OVER() AS total"
        else:
            # Otherwise, no need for obj_field in count, less DB buffers
            extra_col = ", 0 AS total"

        # The following hint is needed until we sort out why, time to time, there is a FTS on obj_head
        sql = """
    SET LOCAL enable_seqscan=FALSE;
    SELECT obh.objid, obh.acquisid, obh.sampleid %s
      FROM """ % extra_col + from_.get_sql() + " " + where.get_sql()

        # Add order & window if relevant
        if order_clause is not None:
            sql += order_clause.get_sql()
        if window_start is not None:
            sql += " OFFSET %d" % window_start
        if window_size is not None:
            sql += " LIMIT %d" % window_size

        with CodeTimer("query: for %d using %s " % (proj_id, sql), logger):
            res: ResultProxy = self.session.execute(sql, params)
        ids = []
        total = 0
        objid: int
        acquisid: int
        sampleid: int
        for objid, acquisid, sampleid, total in res:  # type:ignore
            ids.append((objid, acquisid, sampleid, proj_id))

        if total == 0:
            # Total was not computed or left to 0
            total, _nbr_v, _nbr_d, _nbr_p = self.summary(current_user_id, proj_id, filters, True)

        return ids, total

    @staticmethod
    def cook_order_clause(order_field: Optional[str]) -> Optional[OrderClause]:
        """
            Prepare a SQL "order by" clause from the required field.
        """
        ret = None
        if order_field is not None:
            ret = OrderClause()
            asc_desc = None
            if order_field[0] == "-":
                asc_desc = "DESC"
                order_field = order_field[1:]
            if order_field == "classifname":
                order_field_alias = "txo"
                order_field = "name"
            elif order_field in ObjectHeader.__dict__:
                order_field_alias = "obh"
            else:
                order_field_alias = "obf"
            ret.add_expression(order_field_alias, order_field, asc_desc)
            # Disambiguate using obj_id
            ret.add_expression("obh", "objid", asc_desc)
        return ret

    def parents_by_id(self, current_user_id: UserIDT, object_ids: ObjectIDListT) -> ObjectIDWithParentsListT:
        """
            Query the given IDs, return parents.
        """
        # Security check
        obj_set = EnumeratedObjectSet(self.session, object_ids)
        # Get project IDs for the objects and verify rights
        prj_ids = obj_set.get_projects_ids()
        for a_prj_id in prj_ids:
            RightsBO.user_wants(self.session, current_user_id, Action.READ, a_prj_id)

        sql = """
    SELECT objid, acquisid, sampleid, projid
      FROM obj_head obh 
     WHERE obh.objid = any (:ids) """
        params = {"ids": object_ids}

        res: ResultProxy = self.session.execute(sql, params)
        ids = [(objid, acquisid, acquisid, sampleid, projid)
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
        object_set: DescribedObjectSet = DescribedObjectSet(self.session, proj_id, filters)
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
            res: ResultProxy = self.session.execute(sql, params)

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

    def collect_classif(self, histo: List[HistoricalLastClassif]) -> ClassifIDSetT:
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

    def classify_set(self, current_user_id: UserIDT, target_ids: ObjectIDListT, classif_ids: ClassifIDListT,
                     wanted_qualif: str) -> Tuple[int, int, Dict]:
        """
            Classify or validate/set to dubious a set of objects.
        """
        # Get the objects and project, checking rights at the same time.
        object_set, project = self._the_project_for(current_user_id, target_ids, Action.ANNOTATE)
        # Do the raw classification with history.
        nb_upd, all_changes = object_set.classify_validate(current_user_id, classif_ids, wanted_qualif)
        # Propagate changes to update projects_taxo_stat
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
        # Return status
        return nb_upd, project.projid, all_changes

    @staticmethod
    def count_in_and_out(cumulated_changes, classif_id, qualif, inc_or_dec):
        """ Cumulate change +/- for a given taxon """
        if classif_id is None:
            classif_id = -1  # Unclassified
        changes_for_id = cumulated_changes.setdefault(classif_id, {'n': 0, 'V': 0, 'P': 0, 'D': 0})
        changes_for_id['n'] += inc_or_dec
        if qualif in ('V', 'P', 'D'):
            changes_for_id[qualif] += inc_or_dec
