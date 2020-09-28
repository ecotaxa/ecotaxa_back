# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Union, Tuple

from API_models.crud import CreateProjectReq, ProjectSearchResult
from BO.ObjectSet import EnumeratedObjectSet
from BO.Project import ProjectBO
from BO.Rights import RightsBO, Action
from DB import Sample
from DB.Project import Project, ANNOTATE
from DB.User import User
from DB.helpers.ORM import clone_of
from FS.VaultRemover import VaultRemover
from helpers.DynamicLogs import get_logger
from ..helpers.Service import Service

logger = get_logger(__name__)


class ProjectsService(Service):
    """
        Basic CRUD API_operations on Projects
    """

    def create(self, current_user_id: int,
               req: CreateProjectReq) -> Union[int, str]:
        """
            Create a project, eventually as a shallow copy of another.
        """
        current_user, project = RightsBO.user_wants(self.session, current_user_id, Action.CREATE_PROJECT)
        if req.clone_of_id:
            prj = self.session.query(Project).get(req.clone_of_id)
            if prj is None:
                return "Project to clone not found"
            prj = clone_of(prj)
        else:
            prj = Project()
        prj.title = req.title
        prj.status = ANNOTATE
        prj.visible = req.visible
        self.session.add(prj)
        self.session.flush()  # to get the project ID
        # Add the manage privilege
        RightsBO.grant(current_user, Action.ADMINISTRATE, prj)
        self.session.commit()
        return prj.projid

    def search(self, current_user_id: int,
               for_managing: bool = False,
               also_others: bool = False,
               title_filter: str = '',
               instrument_filter: str = '',
               filter_subset: bool = False) -> List[ProjectSearchResult]:
        # No rights checking as basically everyone can see all projects
        current_user: User = self.session.query(User).get(current_user_id)
        ret = []
        # TODO: Better perf by going thru the iterator instead of a list?
        for prj in ProjectBO.projects_for_user(self.session, current_user, for_managing, also_others,
                                               title_filter, instrument_filter, filter_subset):
            ret.append(prj)
        return ret

    def query(self, current_user_id: int,
              prj_id: int,
              for_managing: bool) -> Project:
        current_user, project = RightsBO.user_wants(self.session, current_user_id,
                                                    Action.ADMINISTRATE if for_managing else Action.READ,
                                                    prj_id)
        # For mypy check. Explanation: should the project be not found, there has been an assertion which failed before,
        # so we don't reach this line.
        assert project is not None

        return project

    DELETE_CHUNK_SIZE = 400

    def delete(self, current_user_id: int,
               prj_id: int,
               only_objects: bool) -> Tuple[int, int, int, int]:
        # Security barrier
        _current_user, _project = RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, prj_id)
        # Troll-ish way of erasing
        all_object_ids = ProjectBO.get_all_object_ids(self.session, prj_id=prj_id)
        # Build a big set
        obj_set = EnumeratedObjectSet(self.session, all_object_ids)

        # Prepare a remover thread that will run in // with DB queries
        remover = VaultRemover(self.link_src, logger).do_start()
        # Do the deletion itself.
        nb_objs, nb_img_rows, img_files = obj_set.delete(self.DELETE_CHUNK_SIZE, remover.add_files)

        ProjectBO.delete_object_parents(self.session, prj_id)

        if only_objects:
            # Update stats, should all be 0...
            ProjectBO.update_taxo_stats(self.session, prj_id)
            # Stats depend on taxo stats
            ProjectBO.update_stats(self.session, prj_id)
        else:
            ProjectBO.delete(self.session, prj_id)

        self.session.commit()
        # Wait for the files handled
        remover.wait_for_done()
        return nb_objs, 0, nb_img_rows, len(img_files)

    def recompute_geo(self, current_user_id: int,
                      prj_id: int):
        # Security barrier
        _current_user, _project = RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, prj_id)
        Sample.propagate_geo(self.session, prj_id)
