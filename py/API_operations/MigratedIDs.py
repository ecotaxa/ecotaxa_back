# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)

from typing import List

from API_models.misc import MigratedIDsRsp
from DB.MigratedIDs import ObjidOld2New, SampleIdOld2New, AcquisIdOld2New
from .helpers.Service import Service


class MigratedIDsService(Service):
    """
    Service to retrieve migrated IDs from old IDs.
    """

    def get_migrated_ids(
        self,
        proj_ids: List[int],
        sam_ids: List[int],
        acq_ids: List[int],
        obj_ids: List[int],
    ) -> MigratedIDsRsp:

        res = MigratedIDsRsp(projects={}, samples={}, acquisitions={}, objects={})

        if proj_ids:
            mapping = {1: 13, 3: 16, 4: 17, 6: 19, 8: 20, 10: 21}
            for pid in proj_ids:
                if pid in mapping:
                    res.projects[pid] = mapping[pid]

        if sam_ids:
            q = self.ro_session.query(SampleIdOld2New).filter(
                SampleIdOld2New.old_id.in_(sam_ids)
            )
            for row in q:
                res.samples[row.old_id] = row.new_id

        if acq_ids:
            q = self.ro_session.query(AcquisIdOld2New).filter(
                AcquisIdOld2New.old_id.in_(acq_ids)
            )
            for row in q:
                res.acquisitions[row.old_id] = row.new_id

        if obj_ids:
            q = self.ro_session.query(ObjidOld2New).filter(
                ObjidOld2New.old_id.in_(obj_ids)
            )
            for row in q:
                res.objects[row.old_id] = row.new_id

        return res
