# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Final

from DB.helpers.Direct import text
from DB.helpers.ORM import Session


class ProjectPrivilegeBO(object):
    """
    Project privilege business object. So far just a container for API_operations involving it.
    """

    # TODO: Put in SQL below
    MANAGE: Final = "Manage"
    ANNOTATE: Final = "Annotate"
    VIEW: Final = "View"

    @classmethod
    def managers_by_project(cls) -> str:
        """
        Return SQL chunk for all managers for all projects.
        """
        return (
            """ SELECT u.email, u.name, pp.projid, rank() 
                         OVER (PARTITION BY pp.projid ORDER BY pp.id) rang
                         FROM projectspriv pp 
                         JOIN users u ON pp.member = u.id
                        WHERE pp.privilege = '"""
            + cls.MANAGE
            + """' 
                      AND u.active = true """
        )

    @classmethod
    def first_manager_by_project(cls) -> str:
        """
        Return SQL chunk for historically first manager for projects in this query.
        """
        # noinspection SqlResolve
        return (
            """ SELECT * from ( """
            + cls.managers_by_project()
            + """ ) qpp 
                    WHERE rang = 1 """
        )

    @classmethod
    def generous_merge_into(cls, session: Session, dest_prj_id: int, src_prj_id: int):
        """
        Merge privileges from source project into destination project.
        """
        # Each user who is present in both projects, gets the highest privilege from both projects.
        # TODO: Arguable
        sql = text(
            """
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
        )
        session.execute(sql, {"dst_prj": dest_prj_id, "src_prj": src_prj_id})
        # Users who were only in source project get their privileges transferred into destination
        # TODO: Arguable
        sql = text(
            """
                UPDATE projectspriv
                   SET projid = :dst_prj 
                 WHERE projid = :src_prj 
                   AND member NOT IN (SELECT member 
                                        FROM projectspriv 
                                       WHERE projid = :dst_prj)"""
        )

        session.execute(sql, {"dst_prj": dest_prj_id, "src_prj": src_prj_id})
