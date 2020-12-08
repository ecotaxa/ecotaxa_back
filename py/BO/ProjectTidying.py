# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Various entities inside a project obey to some rules about naming & relationship
#
from typing import Dict, Set, List, Optional

from BO.Acquisition import AcquisitionOrigIDT
from BO.Object import ObjectIDT
from BO.Project import ProjectIDT
from BO.Sample import SampleOrigIDT
from DB import Sample, Acquisition, ObjectHeader
from DB import Session
from DB.helpers.ORM import Query


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

    def read_from_db(self, session: Session, prj_id: ProjectIDT):
        """
            Read the project topology from DB.
        """
        qry: Query = session.query(Sample, Acquisition, ObjectHeader)
        qry = qry.filter(ObjectHeader.projid == prj_id)
        qry = qry.join(Sample).join(Acquisition)
        sam: Sample
        acq: Acquisition
        obj: ObjectHeader
        for sam, acq, obj in qry.all():
            # Get/create acquisitions for this sample
            objs_for_acquisition = self.add_association(sam.orig_id, acq.orig_id)
            # Store objects for acquisition
            objs_for_acquisition.add(obj.objid)

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
                           % (acquis_user_id, parents))
        return ret
