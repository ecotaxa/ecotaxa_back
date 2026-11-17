# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Various entities inside a project obey to some rules about naming & relationship
#
from typing import Dict, Set, List, Optional

from sqlalchemy import func

from DB import Session
from DB.Acquisition import Acquisition, AcquisitionOrigIDT
from DB.Process import Process, ProcessOrigIDT
from DB.Project import ProjectIDT
from DB.Sample import Sample, SampleOrigIDT
from DB.helpers import SQL
from DB.helpers.Core import select


class ProjectTopology(object):
    """
    A project structure, described in terms of nested entities with locality rules & relationship between them.
    So far the rules are:
         -1 samples.orig_id AKA sample_id from TSV are unique per project,
            they identify the samples to users.
         -2 acquisitions.orig_id AKA acquis_id from TSV are unique per project,
            they identify the acquisitions to users.
         -3 the relationships b/w Samples and Acquisitions are in ObjectHeader.
         -4 considering the project as the root, samples and acquisitions form a tree.
         -5 Process entities are twin to Acquisitions, their orig_id AKA process_id from TSV is not constrained.
    Rule #4 is not (as of v2.5.0) present yet in DB, due to previous versions of the app.
    For later when #544 is done:
         - orig_id AKA object_id must become unique per project.

    For now, only the sample/acquisition/process relations are kept: objects are not
    needed to check the topology, and keeping their (big) per-acquisition sets
    is expensive on large projects.
    """

    def __init__(self) -> None:
        # Each acquisition (as identified by its orig_id) has a parent, but eventually several of them.
        self.acquisition_parents: Dict[AcquisitionOrigIDT, Set[SampleOrigIDT]] = {}
        # Each acquisition has a child process.
        self.acquisition_child: Dict[AcquisitionOrigIDT, ProcessOrigIDT] = {}

    def read_from_db(self, session: Session, prj_id: ProjectIDT):
        """
        Read the project topology from DB, i.e. the sample/acquisition/process
        relations, one row per relation instead of one per object.
        """
        stmt = (
            select(
                Sample.orig_id,
                Acquisition.orig_id,
                Process.orig_id,
            )
            .select_from(Sample)
            .join(Sample.all_acquisitions)
            .join(Acquisition.process)
            .where(
                Sample.projid == prj_id,
                Acquisition.acquisid.op("<@")(func.acq_in_prj(prj_id)),
            )
            .distinct()
            .execution_options(yield_per=SQL.DB_CHUNK_SIZE * 10)  # 3 columns
        )
        for sam_orig_id, acq_orig_id, prc_orig_id in session.execute(stmt):
            self.add_association(sam_orig_id, acq_orig_id)
            if prc_orig_id is not None:
                self.acquisition_child[acq_orig_id] = prc_orig_id

    def add_association(
        self, sample_orig_id: SampleOrigIDT, acquisition_orig_id: AcquisitionOrigIDT
    ) -> None:
        """
        Add the given association while keeping structures in sync.
        """
        self.acquisition_parents.setdefault(acquisition_orig_id, set()).add(
            sample_orig_id
        )

    def evaluate_add_association(
        self, sample_orig_id: SampleOrigIDT, acquisition_orig_id: AcquisitionOrigIDT
    ) -> Optional[str]:
        """
        Complain if adding the given would lead to damage the wanted topology.
        """
        parents_for_acq = self.acquisition_parents.get(acquisition_orig_id)
        if parents_for_acq is None:
            # Never seen -> OK
            return None
        if sample_orig_id in parents_for_acq:
            # Known association -> OK
            return None
        return (
            "Acquisition '%s' is already associated with sample '%s', it cannot be associated as well with '%s"
            % (acquisition_orig_id, parents_for_acq, sample_orig_id)
        )

    def get_inconsistencies(self) -> List[str]:
        """
        Return messages about eventual inconsistencies in the topology.
        """
        ret = []
        for acquis_user_id, parents in self.acquisition_parents.items():
            if len(parents) > 1:
                ret.append(
                    "Acquisition '%s' is nested in several samples: %s "
                    % (acquis_user_id, parents)
                )  # pragma: no cover
        for acquis_user_id in self.acquisition_parents.keys():
            if acquis_user_id not in self.acquisition_child:
                ret.append(
                    "Acquisition '%s' has no associated Process " % (acquis_user_id,)
                )  # pragma: no cover
        return ret
