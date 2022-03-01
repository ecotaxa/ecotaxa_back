# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Various entities inside a project obey to some rules about naming & relationship
#
from typing import Dict, Set, List, Optional

from BO.Acquisition import AcquisitionOrigIDT
from BO.Object import ObjectIDT
from BO.Process import ProcessOrigIDT
from BO.Sample import SampleOrigIDT
from DB import Session
from DB.Acquisition import Acquisition
from DB.Object import ObjectHeader
from DB.Process import Process
from DB.Project import ProjectIDT
from DB.Sample import Sample


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
    """

    def __init__(self):
        # Every object has a path
        self.paths: Dict[SampleOrigIDT, Dict[AcquisitionOrigIDT, Set[ObjectIDT]]] = {}
        # Each acquisition (as identified by its orig_id) has a parent, but eventually several of them.
        self.acquisition_parents: Dict[AcquisitionOrigIDT, Set[SampleOrigIDT]] = {}
        # Each acquisition has a child process.
        self.acquisition_child: Dict[AcquisitionOrigIDT, ProcessOrigIDT] = {}

    def read_from_db(self, session: Session, prj_id: ProjectIDT):
        """
            Read the project topology from DB.
        """
        qry = session.query(Sample)
        qry = qry.join(Sample.all_acquisitions)
        qry = qry.join(Acquisition.process)
        qry = qry.join(Acquisition.all_objects)
        qry = qry.filter(Sample.projid == prj_id)
        qry = qry.with_entities(Sample.orig_id, Acquisition.orig_id, Process.orig_id, ObjectHeader.objid)
        sam_orig_id: str
        acq_orig_id: str
        prc_orig_id: str
        objid: ObjectIDT
        for sam_orig_id, acq_orig_id, prc_orig_id, objid in qry:
            # Get/create acquisitions for this sample
            objs_for_acquisition = self.add_association(sam_orig_id, acq_orig_id)
            # Store twin process
            if prc_orig_id is not None:
                self.acquisition_child[acq_orig_id] = prc_orig_id
            # Store objects for acquisition
            objs_for_acquisition.add(objid)

    def add_association(self, sample_orig_id: SampleOrigIDT, acquisition_orig_id: AcquisitionOrigIDT):
        """
            Add the given association while keeping structures in sync.
        """
        acqs_for_sample = self.paths.setdefault(sample_orig_id, {})
        # Store new acquisition...
        if acquisition_orig_id not in acqs_for_sample:
            acqs_for_sample[acquisition_orig_id] = set()
            # ...and the association with its parent sample
            parent_samples = self.acquisition_parents.setdefault(acquisition_orig_id, set())
            parent_samples.add(sample_orig_id)
        objs_for_acquisition = acqs_for_sample[acquisition_orig_id]
        return objs_for_acquisition

    def evaluate_add_association(self, sample_orig_id: SampleOrigIDT, acquisition_orig_id: AcquisitionOrigIDT) -> \
            Optional[str]:
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
        return ("Acquisition '%s' is already associated with sample '%s', it cannot be associated as well with '%s" %
                (acquisition_orig_id, parents_for_acq, sample_orig_id))

    def get_inconsistencies(self) -> List[str]:
        """
            Return messages about eventual inconsistencies in the topology.
        """
        ret = []
        for acquis_user_id, parents in self.acquisition_parents.items():
            if len(parents) > 1:
                ret.append("Acquisition '%s' is nested in several samples: %s "
                           % (acquis_user_id, parents))  # pragma: no cover
        for acquis_user_id in self.acquisition_parents.keys():
            if acquis_user_id not in self.acquisition_child:
                ret.append("Acquisition '%s' has no associated Process "
                           % (acquis_user_id,))  # pragma: no cover
        return ret
