# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from DB.helpers.ORM import Session


class ProjectPrivilegeBO(object):
    """
        Project privilege business object. So far just a container for API_operations involving it.
    """
    # TODO: Put in SQL below
    MANAGE = 'Manage'
    ANNOTATE = 'Annotate'
    VIEW = 'View'

    @classmethod
    def generous_merge_into(cls, session: Session, dest_prj_id: int, src_prj_id: int):
        """
            Merge privileges from source project into destination project.
        """
        # Each user who is present in both projects, gets the highest privilege from both projects.
        # TODO: Arguable
        sql = """
               UPDATE projectspriv ppdst
                  SET privilege = CASE WHEN 'Manage' IN (ppsrc.privilege, ppdst.privilege) 
                                           THEN 'Manage'
                                       WHEN 'Annotate' IN (ppsrc.privilege, ppdst.privilege) 
                                           THEN 'Annotate'
                                       ELSE 'View' 
                                  END
                 FROM projectspriv ppsrc
                WHERE ppsrc.projid = :src_prj 
                  AND ppdst.projid = :dst_prj 
                  AND ppsrc.member = ppdst.member"""
        session.execute(sql, {"dst_prj": dest_prj_id,
                              "src_prj": src_prj_id})
        # Users who were only in source project get their privileges transferred into destination
        # TODO: Arguable
        sql = """
                UPDATE projectspriv
                   SET projid = :dst_prj 
                 WHERE projid = :src_prj 
                   AND member NOT IN (SELECT member 
                                        FROM projectspriv 
                                       WHERE projid = :dst_prj)"""

        session.execute(sql, {"dst_prj": dest_prj_id,
                              "src_prj": src_prj_id})
