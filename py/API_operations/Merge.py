# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Dict

from API_models.merge import MergeRsp
from BO.Mappings import ProjectMapping, RemapOp, MAPPED_TABLES, MappedTableTypeT
from BO.Project import ProjectBO
from BO.ProjectPrivilege import ProjectPrivilegeBO
from BO.Rights import RightsBO, Action
from DB import ObjectHeader, Sample, Acquisition, Process, Project, ParticleProject
from helpers.DynamicLogs import get_logger
from .helpers.Service import Service

# noinspection PyProtectedMember

logger = get_logger(__name__)


class MergeService(Service):
    """
        Merge operation, move everything from source into destination project.
    """

    def __init__(self, prj_id: int, src_prj_id: int, dry_run: bool):
        super().__init__()
        # params
        self.prj_id = prj_id
        self.src_prj_id = src_prj_id
        self.dry_run = dry_run
        # work vars
        self.remap_operations: Dict[MappedTableTypeT, List[RemapOp]] = {}
        self.dest_augmented_mappings = ProjectMapping()

    def run(self, current_user_id: int) -> MergeRsp:
        """
            Run the service, merge the projects.
        :return:
        """
        # Security check
        RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, self.prj_id)
        RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, self.src_prj_id)
        # OK
        prj = self.session.query(Project).get(self.prj_id)
        src_prj = self.session.query(Project).get(self.src_prj_id)

        logger.info("Validating Merge of '%s'", prj.title)
        ret = MergeRsp()
        errs = self._verify_possible(prj, src_prj)
        ret.errors = errs
        # Exit if errors or dry run
        if self.dry_run or len(errs) > 0:
            return ret

        logger.info("Remaps: %s", self.remap_operations)
        # Go for real if not dry run AND len(errs) == 0
        logger.info("Starting Merge of '%s'", prj.title)
        self._do_merge(prj)
        # Recompute stats and so on
        ProjectBO.do_after_load(self.session, prj_id=self.prj_id)
        return ret

    def _verify_possible(self, dest_prj: Project, src_prj: Project) -> List[str]:
        """
            Verify that the merge would not mean a loss of information.
                The mappings of src project should be preserved and copied into dest project.
                Augmented mappings should fit in the allowed maximum size for each entity.
            :param dest_prj:
            :param src_prj:
            :return: a list of problems, empty means we can proceed.
        """
        ret = []
        dest_mappings = ProjectMapping().load_from_project(dest_prj)
        src_mappings = ProjectMapping().load_from_project(src_prj)
        a_tbl: MappedTableTypeT
        for a_tbl in MAPPED_TABLES:
            mappings_for_dest_tbl = dest_mappings.by_table[a_tbl]
            mappings_for_src_tbl = src_mappings.by_table[a_tbl]
            # Compute the new mapping and eventual transformations to get there
            aug, remaps, errs = mappings_for_dest_tbl.augmented_with(mappings_for_src_tbl)
            ret.extend(errs)
            if len(remaps) > 0:
                self.remap_operations[a_tbl] = remaps
            # Load future mapping
            self.dest_augmented_mappings.by_table[a_tbl].load_from(aug)
        return ret

    def _do_merge(self, dest_prj: Project):
        """
            Real merge operation.
        """
        # Loop over involved tables and remap
        for a_mapped_tbl in MAPPED_TABLES:
            remaps = self.remap_operations.get(a_mapped_tbl)
            # Do the remappings if any
            if remaps is not None:
                logger.info("Doing re-mapping in %s: %s", a_mapped_tbl.__tablename__, remaps)
                ProjectBO.remap(self.session, self.src_prj_id, a_mapped_tbl, remaps)

        # Loop over tables with FK to project and move
        for a_fk_to_proj_tbl in [Acquisition, Process, Sample, ObjectHeader, ParticleProject]:
            # Move all to dest project
            upd = self.session.query(a_fk_to_proj_tbl)
            upd = upd.filter(a_fk_to_proj_tbl.projid == self.src_prj_id)  # type: ignore
            rowcount = upd.update(values={'projid': self.prj_id}, synchronize_session=False)
            logger.info("Update in %s: %s rows", a_fk_to_proj_tbl.__tablename__, rowcount)

        self.dest_augmented_mappings.write_to_project(dest_prj)

        ProjectPrivilegeBO.generous_merge_into(self.session, self.prj_id, self.src_prj_id)

        # Completely erase the source project
        ProjectBO.delete(self.session, self.src_prj_id)

        # Stats on destination project updated
        ProjectBO.do_after_load(self.session, self.prj_id)
