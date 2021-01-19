# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Dict, Union

from sqlalchemy import func

from API_models.merge import MergeRsp
from BO.Acquisition import AcquisitionIDT
from BO.Bundle import InBundle
from BO.Mappings import ProjectMapping, RemapOp, MAPPED_TABLES, MappedTableTypeT
from BO.Project import ProjectBO
from BO.ProjectPrivilege import ProjectPrivilegeBO
from BO.Rights import RightsBO, Action
from BO.Sample import SampleIDT
from DB import ObjectHeader, Sample, Acquisition, Project, ParticleProject
from DB.helpers.ORM import orm_equals, any_, all_, Query
from DB.helpers.Postgres import values_cte
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

        # Also check problems on consistency of unique orig_id
        dest_parents = InBundle.fetch_existing_parents(self.session, prj_id=self.prj_id)
        src_parents = InBundle.fetch_existing_parents(self.session, prj_id=self.src_prj_id)

        for an_orig_id_container in [Sample.__tablename__, Acquisition.__tablename__]:
            # key=orig_id value, value=full record
            dest_orig_ids = dest_parents[an_orig_id_container]
            src_orig_ids = src_parents[an_orig_id_container]
            common_orig_ids = set(dest_orig_ids.keys()).intersection(src_orig_ids.keys())
            if len(common_orig_ids) != 0:
                logger.info("Common %s orig_ids: %s", an_orig_id_container, common_orig_ids)
            for common_orig_id in common_orig_ids:
                orm_diff = orm_equals(dest_orig_ids[common_orig_id], src_orig_ids[common_orig_id])
                if orm_diff:
                    msg = ("Data conflict: %s record with orig_id '%s' is different in destination project: %s"
                           % (an_orig_id_container, common_orig_id, str(orm_diff)))
                    # TODO: Should be an error?
                    logger.warning(msg)
        return ret

    def _do_merge(self, dest_prj: Project):
        """
            Real merge operation.
        """
        # Loop over involved tables and remap free columns
        for a_mapped_tbl in MAPPED_TABLES:
            remaps = self.remap_operations.get(a_mapped_tbl)
            # Do the remappings if any
            if remaps is not None:
                logger.info("Doing re-mapping in %s: %s", a_mapped_tbl.__tablename__, remaps)
                ProjectBO.remap(self.session, self.src_prj_id, a_mapped_tbl, remaps)

        # Collect orig_id
        dest_parents = InBundle.fetch_existing_parents(self.session, prj_id=self.prj_id)
        src_parents = InBundle.fetch_existing_parents(self.session, prj_id=self.src_prj_id)

        # Compute needed projections in order to keep orig_id unicity
        common_samples = self.get_ids_for_common_orig_id(Sample, dest_parents, src_parents)
        common_acquisitions = self.get_ids_for_common_orig_id(Acquisition, dest_parents, src_parents)

        # Align foreign keys, to Project, Sample and Acquisition
        for a_fk_to_proj_tbl in [Sample, Acquisition, ObjectHeader, ParticleProject]:
            upd: Query = self.session.query(a_fk_to_proj_tbl)
            if a_fk_to_proj_tbl == Sample:
                # Move (i.e. change project) samples which are 'new' from merged project,
                #    so take all of them from src project...
                upd = upd.filter(a_fk_to_proj_tbl.projid == self.src_prj_id)  # type: ignore
                # ...but not the ones with same orig_id, which are presumably equal.
                upd = upd.filter(Sample.sampleid != all_(list(common_samples.keys())))
                # And update the column
                upd_values = {'projid': self.prj_id}
            elif a_fk_to_proj_tbl == Acquisition:
                # Acquisitions which were created, in source, under new samples, will 'follow'
                #    them during above move, thanks to the FK on acq_sample_id.
                # BUT some acquisitions were potentially created in source project, inside
                #    forked samples. They need to be attached to the dest (self) corresponding sample.
                if len(common_samples) > 0:
                    # Build a CTE with values for the update
                    smp_cte = values_cte("upd_smp", ("src_id", "dst_id"),
                                         [(k, v) for k, v in common_samples.items()])
                    smp_subqry = self.session.query(smp_cte.c.column2).filter(
                        smp_cte.c.column1 == Acquisition.acq_sample_id)
                    upd_values = {'acq_sample_id': func.coalesce(smp_subqry.as_scalar(), Acquisition.acq_sample_id)}
                    upd = upd.filter(Acquisition.acq_sample_id == any_(list(common_samples.keys())))
                    # upd = upd.filter(Acquisition.acquisid != all_(list(common_acquisitions.keys())))
                else:
                    # Nothing to do. There were only new samples, all of them moved to self.
                    continue
            elif a_fk_to_proj_tbl == ObjectHeader:
                # Generated SQL looks like:
                # with upd_smp (src_id, dst_id) as (values (5,6), (7,8)),
                #      upd_acq (src_id, dst_id) as (values (5,6), (7,8))
                # update obj_head
                #    set sampleid = coalesce((select dst_id from upd_smp where sampleid=src_id), sampleid),
                #        acquisid = coalesce((select dst_id from upd_acq where acquisid=src_id), acquisid)
                #        projid = 1234567
                # where projid=3455
                upd_values = {'projid': self.prj_id}
                upd = upd.filter(ObjectHeader.projid == self.src_prj_id)  # type: ignore
                if len(common_samples) > 0:
                    # Object must follow its sample
                    smp_cte = values_cte("upd_smp", ("src_id", "dst_id"),
                                         [(k, v) for k, v in common_samples.items()])
                    smp_subqry = self.session.query(smp_cte.c.column2).filter(
                        smp_cte.c.column1 == ObjectHeader.sampleid)
                    upd_values['sampleid'] = func.coalesce(smp_subqry.as_scalar(), ObjectHeader.sampleid)
                if len(common_acquisitions) > 0:
                    # Object must follow its acquisition
                    acq_cte = values_cte("upd_acq", ("src_id", "dst_id"),
                                         [(k, v) for k, v in common_acquisitions.items()])
                    acq_subqry = self.session.query(acq_cte.c.column2).filter(
                        acq_cte.c.column1 == ObjectHeader.acquisid)
                    upd_values['acquisid'] = func.coalesce(acq_subqry.as_scalar(), ObjectHeader.acquisid)
            else:
                # For Particle project
                upd_values = {'projid': self.prj_id}
            rowcount = upd.update(values=upd_values, synchronize_session=False)
            logger.info("Update in %s: %s rows", a_fk_to_proj_tbl.__tablename__, rowcount)

        # Acquisition & twin Process have followed their enclosing Sample

        # Remove the parents which are duplicate from orig_id point of view
        for a_fk_to_proj_tbl in [Acquisition, Sample]:
            to_del: Query = self.session.query(a_fk_to_proj_tbl)
            if a_fk_to_proj_tbl == Acquisition:
                # Remove conflicting acquisitions, they should be empty?
                to_del = to_del.filter(
                    Acquisition.acquisid == any_(list(common_acquisitions.keys())))  # type: ignore
            elif a_fk_to_proj_tbl == Sample:
                # Remove conflicting samples
                to_del = to_del.filter(
                    Sample.sampleid == any_(list(common_samples.keys())))  # type: ignore
            rowcount = to_del.delete(synchronize_session=False)
            logger.info("Delete in %s: %s rows", a_fk_to_proj_tbl.__tablename__, rowcount)

        self.dest_augmented_mappings.write_to_project(dest_prj)

        ProjectPrivilegeBO.generous_merge_into(self.session, self.prj_id, self.src_prj_id)

        # Completely erase the source project
        ProjectBO.delete(self.session, self.src_prj_id)

    @staticmethod
    def get_ids_for_common_orig_id(a_parent_class, dest_parents, src_parents) -> \
            Dict[Union[SampleIDT, AcquisitionIDT], Union[SampleIDT, AcquisitionIDT]]:
        """
            Return a link between IDs for resolving colliding orig_id.
            E.g. sample 'moose2015_ge_leg2_026' is present in source with ID 15482
                and also in destination with ID 84678
            -> return {15482:84678}, to read 15482->84678
        :param a_parent_class: Sample/Acquisition
        :param dest_parents:
        :param src_parents:
        :return:
        """
        ret = {}
        dst_orig_ids = dest_parents[a_parent_class.__tablename__]
        src_orig_ids = src_parents[a_parent_class.__tablename__]
        common_orig_ids = set(dst_orig_ids.keys()).intersection(src_orig_ids.keys())
        for a_common_orig_id in common_orig_ids:
            src_orig_id = src_orig_ids[a_common_orig_id].pk()
            dst_orig_id = dst_orig_ids[a_common_orig_id].pk()
            ret[src_orig_id] = dst_orig_id
        return ret
