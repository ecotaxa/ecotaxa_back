# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Dict, Union

from API_models.merge import MergeRsp
from BO.Acquisition import AcquisitionIDT
from BO.Bundle import InBundle
from BO.Mappings import ProjectMapping, RemapOp, MAPPED_TABLES, MappedTableTypeT
from BO.Project import ProjectBO
from BO.ProjectPrivilege import ProjectPrivilegeBO
from BO.Rights import RightsBO, Action
from BO.Sample import SampleIDT
from DB.Acquisition import Acquisition
from DB.Object import ObjectHeader
from DB.Process import Process
from DB.Project import Project
from DB.Sample import Sample
from DB.helpers.ORM import orm_equals, any_, all_, clone_of
from DB.helpers.Postgres import text
from helpers.DynamicLogs import get_logger
from .helpers.Service import Service

logger = get_logger(__name__)


class MergeService(Service):
    """
    Merge operation, move everything from source into a destination project.
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
        return self.do_run(current_user_id)

    def do_run(self, current_user_id: int) -> MergeRsp:
        """
            Run the service, merge the projects.
        :return:
        """
        # Security check
        RightsBO.user_wants(
            self.session, current_user_id, Action.ADMINISTRATE, self.prj_id
        )
        RightsBO.user_wants(
            self.session, current_user_id, Action.ADMINISTRATE, self.src_prj_id
        )
        # OK
        prj = self.session.query(Project).get(self.prj_id)
        assert prj is not None
        src_prj = self.session.query(Project).get(self.src_prj_id)
        assert src_prj is not None

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
        self.session.commit()

        # Recompute stats and so on
        ProjectBO.do_after_load(self.session, prj_id=self.prj_id)
        self.session.commit()
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
        if dest_prj.instrument_id != src_prj.instrument_id:
            ret.append("Source and target projects have different instruments")
        dest_mappings = ProjectMapping().load_from_project(dest_prj)
        src_mappings = ProjectMapping().load_from_project(src_prj)
        a_tbl: MappedTableTypeT
        for a_tbl in MAPPED_TABLES:
            mappings_for_dest_tbl = dest_mappings.by_table[a_tbl]
            mappings_for_src_tbl = src_mappings.by_table[a_tbl]
            # Compute the new mapping and eventual transformations to get there
            aug, remaps, errs = mappings_for_dest_tbl.augmented_with(
                mappings_for_src_tbl
            )
            ret.extend(errs)
            if len(remaps) > 0:
                self.remap_operations[a_tbl] = remaps
            # Load future mapping
            self.dest_augmented_mappings.by_table[a_tbl].load_from(aug)

        # Also check problems on consistency of unique orig_id
        src_samples, src_acquisitions = InBundle.fetch_existing_parents(
            self.ro_session, prj_id=self.src_prj_id
        )
        dest_samples, dest_acquisitions = InBundle.fetch_existing_parents(
            self.ro_session, prj_id=self.prj_id
        )

        def verif(container: str, src_entities: Dict, dest_entities: Dict) -> None:
            common_orig_ids = set(dest_entities.keys()).intersection(
                src_entities.keys()
            )
            if len(common_orig_ids) != 0:
                logger.info("Common %s orig_ids: %s", container, common_orig_ids)
            for common_orig_id in common_orig_ids:
                orm_diff = orm_equals(
                    dest_entities[common_orig_id], src_entities[common_orig_id]
                )
                if orm_diff:
                    msg = (
                        "Data conflict: %s record with orig_id '%s' is different in destination project: %s"
                        % (container, common_orig_id, str(orm_diff))
                    )
                    # TODO: Should be an error?
                    logger.warning(msg)

        verif(Sample.__tablename__, src_samples, dest_samples)
        verif(Acquisition.__tablename__, src_acquisitions, dest_acquisitions)
        return ret

    def _do_merge(self, dest_prj: Project) -> None:
        """
        Real merge operation.
        """
        # Loop over involved tables and remap free columns
        for a_mapped_tbl in MAPPED_TABLES:
            remaps = self.remap_operations.get(a_mapped_tbl)
            # Do the remappings if any
            if remaps is not None:
                logger.info(
                    "Doing re-mapping in %s: %s", a_mapped_tbl.__tablename__, remaps
                )
                ProjectBO.remap(self.session, self.src_prj_id, a_mapped_tbl, remaps)

        # Collect orig_id
        src_samples, src_acquisitions = InBundle.fetch_existing_parents(
            self.ro_session, prj_id=self.src_prj_id
        )
        dest_samples, dest_acquisitions = InBundle.fetch_existing_parents(
            self.ro_session, prj_id=self.prj_id
        )

        # Compute needed projections in order to keep orig_id unicity
        common_samples = self.get_ids_for_common_orig_id(dest_samples, src_samples)
        common_acquisitions = self.get_ids_for_common_orig_id(
            dest_acquisitions, src_acquisitions
        )

        # Identify all acquisitions from src project that are NOT in common_acquisitions
        # We fetch them BEFORE moving samples to keep src_prj_id filter working .
        # Let's use src_samples keys (which are orig_ids) to be safe.
        acqs_to_move = (
            self.session.query(Acquisition)
            .join(Sample)
            .filter(Sample.projid == self.src_prj_id)
            .filter(Acquisition.acquisid != all_(list(common_acquisitions.keys())))
            .order_by(Acquisition.acquisid)
            .all()
        )

        # Fetch all objects from src project that are NOT under common acquisitions
        # (Those under common acquisitions will be handled later)
        objs_to_move = (
            self.session.query(ObjectHeader.objid)
            .join(Acquisition)
            .join(Sample)
            .filter(Sample.projid == self.src_prj_id)
            .filter(Acquisition.acquisid != all_(list(common_acquisitions.keys())))
            .order_by(ObjectHeader.objid)
            .all()
        )
        objs_to_move = [o.objid for o in objs_to_move]

        # 1. Renumber samples
        # Identify samples from src project that are NOT in common_samples
        samples_to_move = (
            self.session.query(Sample)
            .filter(Sample.projid == self.src_prj_id)
            .filter(Sample.sampleid != all_(list(common_samples.keys())))
            .order_by(Sample.sampleid)
            .all()
        )
        if samples_to_move:
            for smp in samples_to_move:
                old_sampleid = smp.sampleid
                new_sampleid = Sample.get_next_pk(self.session, self.prj_id)
                logger.info("Moving sample %d to %d", old_sampleid, new_sampleid)

                # 1. Create a new record in samples with the new ID and project ID
                new_smp = clone_of(smp)
                new_smp.sampleid = new_sampleid
                new_smp.projid = self.prj_id
                self.session.add(new_smp)

        # 2. Renumber acquisitions
        # Identify acquisitions that now belong to dest project (either moved with sample or moved below)
        # We renumber ALL acquisitions from the source project that are NOT in common_acquisitions
        if acqs_to_move:
            for acq in acqs_to_move:
                old_acquisid = acq.acquisid
                new_acquisid = Acquisition.get_next_pk(self.session, self.prj_id)
                logger.info("Moving acquisition %d to %d", old_acquisid, new_acquisid)

                # 1. Create a new record in acquisitions with the new ID
                # We also need to get the NEW sample ID if it was renumbered
                # Or use the old one if it was common.
                old_s_id = acq.acq_sample_id
                # Check if it was renumbered
                new_s_id_res = (
                    self.session.query(Sample.sampleid)
                    .filter(Sample.projid == self.prj_id)
                    .filter(
                        Sample.orig_id
                        == self.session.query(Sample.orig_id)
                        .filter(Sample.sampleid == old_s_id)
                        .scalar_subquery()
                    )
                    .scalar()
                )

                new_acq = clone_of(acq)
                new_acq.acquisid = new_acquisid
                new_acq.acq_sample_id = new_s_id_res
                self.session.add(new_acq)

                # 2. Create a new record in process (twin table)
                # Need to fetch the old process record
                old_proc = self.session.query(Process).get(old_acquisid)
                if old_proc:
                    new_proc = clone_of(old_proc)
                    new_proc.processid = new_acquisid
                    self.session.add(new_proc)

        # 3. Move objects
        if objs_to_move:
            for old_objid in objs_to_move:
                # 1. Find new acquisid in destination project
                old_a_id_res = self.session.execute(
                    text("SELECT acquisid FROM obj_head WHERE objid = :old_objid"),
                    {"old_objid": old_objid},
                ).scalar()

                new_a_id_res = self.session.execute(
                    text(
                        "SELECT a.acquisid FROM acquisitions a JOIN samples s ON a.acq_sample_id = s.sampleid "
                        "WHERE s.projid = :prj_id AND a.orig_id = (SELECT orig_id FROM acquisitions WHERE acquisid = :old_a_id) "
                        "AND s.orig_id = (SELECT s2.orig_id FROM samples s2 JOIN acquisitions a2 ON a2.acq_sample_id = s2.sampleid WHERE a2.acquisid = :old_a_id)"
                    ),
                    {"prj_id": self.prj_id, "old_a_id": old_a_id_res},
                ).scalar()

                # 2. Update obj_head to point to the new acquisid
                # objid remains the same, preserving consistency in all other tables
                self.session.execute(
                    text(
                        "UPDATE obj_head SET acquisid = :new_a_id WHERE objid = :old_id"
                    ),
                    {"new_a_id": new_a_id_res, "old_id": old_objid},
                )

                # 3. Update redundant acquis_id in obj_field
                self.session.execute(
                    text(
                        "UPDATE obj_field SET acquis_id = :new_a_id WHERE objfid = :old_id"
                    ),
                    {"new_a_id": new_a_id_res, "old_id": old_objid},
                )

        # 4. Final alignment for objects whose acquisitions were common
        if common_acquisitions:
            for src_id, dst_id in common_acquisitions.items():
                self.session.execute(
                    text(
                        "UPDATE obj_head SET acquisid = :dst_id WHERE acquisid = :src_id"
                    ),
                    {"dst_id": dst_id, "src_id": src_id},
                )
                self.session.execute(
                    text(
                        "UPDATE obj_field SET acquis_id = :dst_id WHERE acquis_id = :src_id"
                    ),
                    {"dst_id": dst_id, "src_id": src_id},
                )

        # 5. Cleanup: Delete all old records in reverse order
        # Objects were UPDATED, so we don't delete them from obj_head/obj_field
        # We only delete old acquisitions and samples
        if acqs_to_move:
            old_acq_ids = [acq.acquisid for acq in acqs_to_move]
            self.session.execute(
                text("DELETE FROM process WHERE processid = ANY(:old_ids)"),
                {"old_ids": old_acq_ids},
            )
            self.session.execute(
                text("DELETE FROM acquisitions WHERE acquisid = ANY(:old_ids)"),
                {"old_ids": old_acq_ids},
            )

        if samples_to_move:
            old_sam_ids = [smp.sampleid for smp in samples_to_move]
            self.session.execute(
                text("DELETE FROM samples WHERE sampleid = ANY(:old_ids)"),
                {"old_ids": old_sam_ids},
            )

        # Acquisition & twin Process have followed their enclosing Sample
        # Remove the parents which are duplicate from orig_id point of view
        # (This is redundant with cleanup above for non-common ones, but safe for common ones)
        for a_fk_to_proj_tbl in [Acquisition, Sample]:
            to_del = self.session.query(a_fk_to_proj_tbl)
            if a_fk_to_proj_tbl == Acquisition:
                # Remove conflicting acquisitions, they should be empty?
                to_del = to_del.filter(
                    Acquisition.acquisid == any_(list(common_acquisitions.keys()))
                )
            elif a_fk_to_proj_tbl == Sample:
                # Remove conflicting samples
                to_del = to_del.filter(
                    Sample.sampleid == any_(list(common_samples.keys()))
                )
            rowcount = to_del.delete(synchronize_session=False)
            table_name = a_fk_to_proj_tbl.__tablename__  # type: ignore
            logger.info("Delete in %s: %s rows", table_name, rowcount)

        self.dest_augmented_mappings.write_to_project(dest_prj)

        ProjectPrivilegeBO.generous_merge_into(
            self.session, self.prj_id, self.src_prj_id
        )

        # Completely erase the source project
        ProjectBO.delete(self.session, self.src_prj_id)

    @staticmethod
    def get_ids_for_common_orig_id(
        dst_orig_ids, src_orig_ids
    ) -> Dict[Union[SampleIDT, AcquisitionIDT], Union[SampleIDT, AcquisitionIDT]]:
        """
            Return a link between IDs for resolving colliding orig_id.
            E.g. sample 'moose2015_ge_leg2_026' is present in source with ID 15482
                and also in destination with ID 84678
            -> return {15482:84678}, to read 15482->84678
        :param dst_orig_ids:
        :param src_orig_ids:
        :return:
        """
        ret = {}
        common_orig_ids = set(dst_orig_ids.keys()).intersection(src_orig_ids.keys())
        for a_common_orig_id in common_orig_ids:
            # Check if it's Acquisition, if so, we need to compare Sample orig_id too
            src_obj = src_orig_ids[a_common_orig_id]
            dst_obj = dst_orig_ids[a_common_orig_id]
            if isinstance(src_obj, Acquisition):
                # We need to check if the parent sample has the same orig_id
                if src_obj.sample.orig_id == dst_obj.sample.orig_id:
                    ret[src_obj.pk()] = dst_obj.pk()
            else:
                ret[src_obj.pk()] = dst_obj.pk()
        return ret
