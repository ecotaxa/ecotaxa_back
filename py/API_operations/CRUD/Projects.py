# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Union, Tuple, Optional, Dict
from API_models.crud import CreateProjectReq
from BO.Classification import ClassifIDListT, ClassifIDT
from BO.ObjectSet import EnumeratedObjectSet
from BO.Project import (
    ProjectBO,
    ProjectBOSet,
    ProjectTaxoStats,
    ProjectUserStats,
    ProjectColumns,
)
from BO.Collection import MinimalCollectionBO
from BO.ProjectSet import ProjectSetColumnStats, LimitedInCategoriesProjectSet
from BO.Rights import RightsBO, Action, NOT_FOUND
from BO.User import UserIDT
from DB.Project import Project, ANNOTATE_STATUS, ProjectIDT, ProjectIDListT
from DB.Sample import Sample
from DB.User import User
from DB.helpers.ORM import clone_of
from FS.VaultRemover import VaultRemover
from helpers.DynamicLogs import get_logger
from ..helpers.Service import Service
from helpers.FieldListType import FieldListType

logger = get_logger(__name__)


class ProjectsService(Service):
    """
    Basic CRUD API_operations on Projects
    """

    def create(self, current_user_id: int, req: CreateProjectReq) -> Union[int, str]:
        """
        Create a project, eventually as a shallow copy of another.
        """
        if req.clone_of_id:
            # Cloning a project needs only manager rights on the origin
            current_user, prj = RightsBO.user_wants(
                self.session, current_user_id, Action.ADMINISTRATE, req.clone_of_id
            )
            if prj is None:
                return "Project to clone not found"
            new_prj = clone_of(prj)
            new_prj.instrument_id = (
                prj.instrument_id
            )  # instrument is a FK, thus not copied by clone_of()
        else:
            current_user = RightsBO.user_wants_create_project(
                self.session, current_user_id
            )
            new_prj = Project()
            new_prj.instrument_id = req.instrument
        # strip title
        req.title = req.title.strip()
        new_prj.title = req.title
        new_prj.status = ANNOTATE_STATUS
        new_prj.visible = req.visible
        self.session.add(new_prj)
        self.session.flush()  # to get the project ID
        # Add the manage privilege & set user as contact
        RightsBO.grant(self.session, current_user, Action.ADMINISTRATE, new_prj, "C")
        self.session.commit()
        return new_prj.projid

    def search(
        self,
        current_user_id: Optional[int],
        for_managing: bool = False,
        not_granted: bool = False,
        title_filter: str = "",
        instrument_filter: str = "",
        filter_subset: bool = False,
        fields: Optional[str] = FieldListType.default,
    ) -> List[ProjectBO]:
        # current_user: Optional[User]
        if current_user_id is None:
            # For public
            matching_ids = ProjectBO.list_public_projects(self.ro_session, title_filter)
            projects = ProjectBOSet(self.session, matching_ids, public=True)
        else:
            # No rights checking as basically everyone can see all projects
            # current_user = self.ro_session.query(User).get(current_user_id)
            current_user: User = RightsBO.get_user_throw(
                self.ro_session, current_user_id
            )
            # assert current_user is not None
            matching_ids = ProjectBO.projects_for_user(
                self.ro_session,
                current_user,
                for_managing,
                not_granted,
                title_filter,
                instrument_filter,
                filter_subset,
            )
            projects = ProjectBOSet(
                self.ro_session, matching_ids, public=False, fields=fields
            )
        return projects.as_list()

    def query(
        self,
        current_user_id: Optional[UserIDT],
        prj_id: int,
        for_managing: bool,
        for_update: bool,
    ) -> ProjectBO:
        if current_user_id is None:
            RightsBO.anonymous_wants(self.ro_session, Action.READ, prj_id)
            highest_right = ""
        else:
            current_user, project = RightsBO.user_wants(
                self.session,
                current_user_id,
                Action.ADMINISTRATE if for_managing else Action.READ,
                prj_id,
            )
            highest_right = RightsBO.highest_right_on(current_user, prj_id)
        ret = ProjectBOSet.get_one(
            self.session if for_update else self.ro_session, prj_id
        )
        assert ret is not None
        ret.highest_right = highest_right
        return ret

    def update_prediction_settings(
        self, current_user_id: UserIDT, prj_id: int, settings: str
    ) -> None:
        assert prj_id is not None
        current_user, project = RightsBO.user_wants(
            self.session, current_user_id, Action.ANNOTATE, prj_id
        )
        project.classifsettings = settings
        self.session.commit()

    DELETE_CHUNK_SIZE = 400

    def delete(
        self, current_user_id: int, prj_id: int, only_objects: bool
    ) -> Tuple[int, int, int, int]:
        # Security barrier
        _current_user, _project = RightsBO.user_wants(
            self.session, current_user_id, Action.ADMINISTRATE, prj_id
        )
        # Troll-ish way of erasing
        all_object_ids = ProjectBO.get_all_object_ids(self.session, prj_id=prj_id)
        # Build a big set
        obj_set = EnumeratedObjectSet(self.session, all_object_ids)

        # Prepare a remover thread that will run in // with DB queries
        remover = VaultRemover(self.config, logger).do_start()
        # Do the deletion itself.
        nb_objs, nb_img_rows, img_files = obj_set.delete(
            self.DELETE_CHUNK_SIZE, remover.add_files
        )

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

    def recompute_geo(self, current_user_id: int, prj_id: ProjectIDT) -> None:
        # Security barrier
        _current_user, _project = RightsBO.user_wants(
            self.session, current_user_id, Action.ADMINISTRATE, prj_id
        )
        Sample.propagate_geo(self.session, prj_id)

    def recompute_sunpos(self, current_user_id: int, prj_id: ProjectIDT) -> int:
        """
        Recompute sun position for every object in the project.
        """
        # Security barrier
        _current_user, _project = RightsBO.user_wants(
            self.session, current_user_id, Action.ADMINISTRATE, prj_id
        )
        return ProjectBO.recompute_sunpos(self.session, prj_id)

    def read_stats(
        self,
        current_user_id: Optional[UserIDT],
        prj_ids: ProjectIDListT,
        taxa_ids: Union[str, ClassifIDListT],
    ) -> List[ProjectTaxoStats]:
        """
        Read classification statistics for these projects.
        """
        # No security barrier because there is no private information inside
        return ProjectBO.read_taxo_stats(self.session, prj_ids, taxa_ids)

    def read_user_stats(
        self, current_user_id: int, prj_ids: ProjectIDListT
    ) -> List[ProjectUserStats]:
        """
        Read user statistics for these projects.
        """
        # Security barrier
        [
            RightsBO.user_wants(
                self.session, current_user_id, Action.ADMINISTRATE, prj_id
            )
            for prj_id in prj_ids
        ]
        ret = ProjectBO.read_user_stats(self.session, prj_ids)
        return ret

    def read_columns_stats(
        self,
        current_user_id: int,
        prj_ids: ProjectIDListT,
        column_names: List[str],
        random_limit: Optional[int],
        categories: List[ClassifIDT],
    ) -> ProjectSetColumnStats:
        """
        Read data statistics for these projects, optionally using a limit and filtering categories.
        """
        # No security barrier because there is no private information inside
        learning_set = LimitedInCategoriesProjectSet(
            self.session, prj_ids, column_names, random_limit, categories
        )
        ret = learning_set.read_columns_stats()
        return ret

    def in_collections(
        self,
        current_user_id: Optional[UserIDT],
        projid: ProjectIDT,
    ) -> List[MinimalCollectionBO]:
        """
        Read classification statistics for these projects.
        """
        # add security barrier ?
        return ProjectBO.in_collections(self.ro_session, projid)

    def read_projects_columns(
        self,
        current_user_id: Optional[UserIDT],
        project_ids: List[int],
        fields: Optional[str] = FieldListType.default,
    ) -> Optional[List[ProjectColumns]]:
        """
        Read values for specific columns for these projects.
        """
        projects = ProjectBOSet(self.ro_session, project_ids, public=False)
        ret = []

        if fields is not None and (
            fields[0 : len(FieldListType.default)] == FieldListType.default.value
            and len(fields) > 1
        ):
            project_columns: Dict = {}
            columns: List = []
            project_columns[FieldListType.default] = [
                "projid",
                "title",
                "instrument",
                "contact",
                "comments",
                "initclassiflist",
                "classiffieldlist",
                "cnn_network_id",
                "license",
                "status",
                "userstats",
            ]
            project_columns[FieldListType.all] = project_columns[
                FieldListType.default
            ] + [
                "mappingobj",
                "mappingsample",
                "mappingprocess",
                "mappingacq",
            ]
            lfields = fields.split(",")
            columns = project_columns[lfields.pop(0)] + lfields
            if len(fields):
                columns.extend(fields.split(","))

        for project in projects.as_list():
            values = []
            for column in columns:
                if hasattr(project, column):
                    values.append(getattr(project, column))
                elif column == "userstats":
                    annotators = ProjectBO.read_user_stats(self.ro_session, project_ids)
                    creators = []
                    for annotator in annotators[1].annotators:
                        creators.append(annotator.id)
                    values.append(creators)
                else:
                    values.append(NOT_FOUND)
            ret.append(ProjectColumns(project.projid, columns, values))
        return ret
