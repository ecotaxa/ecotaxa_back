# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional, List

from API_operations.helpers.Service import Service
from BO.Classification import HistoricalClassification
from BO.Mappings import ProjectMapping
from BO.Object import ObjectBO
from BO.Rights import RightsBO, Action
from DB.Object import ObjectIDT


class ObjectService(Service):
    """
        Basic CRUD operations on a single Object.
            The creation is managed during import.
    """

    def query(self, current_user_id: Optional[int], object_id: ObjectIDT) -> Optional[ObjectBO]:
        ret = ObjectBO(self.ro_session, object_id)
        if not ret.exists():
            return None
        # Security check
        projid = ret.header.acquisition.sample.projid
        if current_user_id is None:
            project = RightsBO.anonymous_wants(self.session, Action.READ, projid)
        else:
            _user, project = RightsBO.user_wants(self.session, current_user_id, Action.READ, projid)
        assert project is not None
        mappings = ProjectMapping().load_from_project(project)
        ret.map_free_columns(mappings.object_mappings)
        return ret

    def query_history(self, current_user_id: Optional[int], object_id: ObjectIDT) \
            -> List[HistoricalClassification]:
        the_obj = ObjectBO(self.ro_session, object_id)
        if not the_obj.exists():
            return []
        # Security check
        # TODO: dup code
        projid = the_obj.header.acquisition.sample.projid
        if current_user_id is None:
            RightsBO.anonymous_wants(self.ro_session, Action.READ, projid)
        else:
            _user, project = RightsBO.user_wants(self.session, current_user_id, Action.READ, projid)
            assert project is not None
        ret = the_obj.get_history()
        return ret
