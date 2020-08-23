# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Tuple, Type

from API_models.merge import MergeRsp
from BO.Project import ProjectBO
from DB import Image, Object, ObjectFields, ObjectCNNFeature, Sample, Acquisition, Process, Project
from helpers.DynamicLogs import get_logger
from .helpers.Service import Service

# noinspection PyProtectedMember

logger = get_logger(__name__)

DBObjectTuple: Type = List[Tuple[Object, ObjectFields, ObjectCNNFeature,
                                 Image, Sample, Acquisition, Process]]


class MergeService(Service):
    """
        Merge operation.
    """

    def __init__(self, current_user: int, prj_id: int, src_prj_id: int):
        super().__init__()
        self.prj_id = prj_id
        self.src_prj_id = src_prj_id

    def run(self) -> MergeRsp:
        """
            Run the service, merge the projects.
        :return:
        """
        prj = self.session.query(Project).get(self.prj_id)
        src_prj = self.session.query(Project).get(self.src_prj_id)
        logger.info("Starting Merge of '%s'", prj.title)
        ret = MergeRsp()

        self._verify_possible()

        self._do_merge()

        # Recompute stats and so on
        ProjectBO.do_after_load(self.session, prj_id=self.prj_id)
        return ret

    def _verify_possible(self):
        pass

    def _do_merge(self):
        pass
