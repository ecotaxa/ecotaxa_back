# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A few services for verifying consistency (DB mainly)
#
from typing import List

from sqlalchemy.orm import Query

from DB import Sample, Project, Acquisition, Process
from DB.helpers.ORM import orm_equals
from .helpers.Service import Service


class ProjectConsistencyChecker(Service):
    """
        With time and bugs, some consistency problems could be introduced in projects.
        This service aims at listing them.
    """

    def __init__(self, current_user_id: int, prj_id: int):
        super().__init__()
        self.prj_id = prj_id
        self.requester_id = current_user_id

    def run(self) -> List[str]:
        ret = []
        # TODO: Permissions
        ret.extend(self.check_duplicate_parents())
        return ret

    def check_duplicate_parents(self) -> List[str]:
        """
            In old merge code, there was no check if e.g. a merged Sample was not the same as a previous
            one in the target project. The PK of Sample table is not the natural one (orig_id) but a generated
            ID from a sequence, so this kind of duplication is possible. Worse case if the clones differ.
            :return:
        """
        ret = []
        for a_tbl in [Sample, Acquisition, Process]:
            tbl_name = a_tbl.__table__
            qry: Query = self.session.query(a_tbl).join(Project)
            qry = qry.filter(Project.projid == self.prj_id)
            qry = qry.order_by(a_tbl.orig_id)
            prev_parent = None
            for a_parent in qry.all():
                if prev_parent and a_parent.orig_id == prev_parent.orig_id:
                    if orm_equals(a_parent, prev_parent):
                        ret.append("In {} orig_id '{}' is fully duplicated (pks {} and {})".
                                   format(tbl_name, a_parent.orig_id, prev_parent.pk(), a_parent.pk()))
                    else:
                        ret.append("In {} orig_id '{}' is equal, but other fields differ (pks {} and {})".
                                   format(tbl_name, a_parent.orig_id, prev_parent.pk(), a_parent.pk()))
                prev_parent = a_parent
        return ret
