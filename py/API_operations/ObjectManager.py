# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Tuple, List, Optional, Set

from API_models.crud import ProjectFilters, ColUpdateList
from BO.Classification import HistoricalClassif, ClassifIDSetT
from BO.ObjectSet import DescribedObjectSet, ObjectIDListT, EnumeratedObjectSet, ObjectIDWithParentsListT
from BO.Project import ProjectBO
from BO.Rights import RightsBO, Action
from BO.Taxonomy import TaxonomyBO, ClassifSetInfoT
from DB.helpers.ORM import ResultProxy
from FS.VaultRemover import VaultRemover
from helpers.DynamicLogs import get_logger
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

    def query(self, current_user_id: int, proj_id: int, filters: ProjectFilters) -> ObjectIDWithParentsListT:
        """
            Query the given project with given filters, return all IDs.
        """
        # Security check
        user, project = RightsBO.user_wants(self.session, current_user_id, Action.READ, proj_id)

        # Prepare a where clause and parameters from filter
        object_set: DescribedObjectSet = DescribedObjectSet(self.session, proj_id, filters)
        where, params = object_set.get_sql(user.id)
        selected_tables = "obj_head oh"
        if "of." in where.get_sql():  # TODO: Duplicated code
            selected_tables += " JOIN obj_field of ON of.objfid = oh.objid"
        sql = "SELECT objid, processid, acquisid, sampleid FROM " + selected_tables + " " + where.get_sql()

        res: ResultProxy = self.session.execute(sql, params)
        # TODO: Below is an obscure record, and no use re-packing something just unpacked
        ids = [(r[0], r[1], r[2], r[3]) for r in res]
        return ids

    def delete(self, current_user_id: int, object_ids: ObjectIDListT) -> Tuple[int, int, int, int]:
        """
            Remove from DB all the objects with ID in given list.
        :return:
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

    def reset_to_predicted(self, current_user_id: int, proj_id: int, filters: ProjectFilters) -> None:
        """
            Query the given project with given filters, reset the resulting objects to predicted.
        """
        # Security check
        RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, proj_id)

        impacted_objs = [r[0] for r in self.query(current_user_id, proj_id, filters)]

        EnumeratedObjectSet(self.session, impacted_objs).reset_to_predicted()

        # Update stats
        ProjectBO.update_taxo_stats(self.session, proj_id)
        # Stats depend on taxo stats
        ProjectBO.update_stats(self.session, proj_id)

    def update_set(self, current_user_id: int, target_ids: ObjectIDListT, updates: ColUpdateList) -> int:
        """
            Update the given set using provided updates.
        """
        # Get project IDs for the processes and verify rights
        object_set = EnumeratedObjectSet(self.session, target_ids)
        prj_ids = object_set.get_projects_ids()
        # All should be in same project, so far
        assert len(prj_ids) == 1, "Too many or no projects for objects: %s" % target_ids
        prj_id = prj_ids[0]
        _user, project = RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, prj_id)
        assert project  # for mypy
        return object_set.apply_on_all(project, updates)

    def revert_to_history(self, current_user_id: int, proj_id: int,
                          filters: ProjectFilters, dry_run: bool,
                          target: Optional[int]) -> Tuple[List[HistoricalClassif], ClassifSetInfoT]:
        """
            Revert to classification history the given set, if dry_run then only simulate.
        """
        # Security check
        RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, proj_id)

        # Get target objects
        impacted_objs = [r[0] for r in self.query(current_user_id, proj_id, filters)]
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
        # Give feeback
        return impact, classifs

    def collect_classif(self, histo: List[HistoricalClassif]) -> ClassifIDSetT:
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
