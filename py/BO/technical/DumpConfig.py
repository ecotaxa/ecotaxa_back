# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Centralized per-table configuration for technical project dump and import.
#
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Tuple

from DB.Acquisition import ACQ_PRJ_OFFSET, Acquisition
from DB.CNNFeatureVector import ObjectCNNFeatureVector
from DB.Collection import Collection, CollectionProject
from DB.Image import Image, ImageFile
from DB.Instrument import Instrument
from DB.Object import OBJ_PRJ_OFFSET, ObjectFields, ObjectHeader, ObjectsClassifHisto
from DB.Prediction import Prediction, PredictionHisto
from DB.Process import Process
from DB.Project import Project, ProjectTaxoStat
from DB.ProjectPrivilege import ProjectPrivilege
from DB.ProjectVariables import ProjectVariables
from DB.Sample import SAM_PRJ_OFFSET, Sample
from DB.TaxoRecast import TaxoRecast
from DB.Taxonomy import Taxonomy
from DB.Training import Training
from DB.User import Organization, User
from DB.UserPreferences import UserPreferences

ProgressCallback = Callable[[int, str], None]


def dedup_progress_cb(
    progress_cb: Optional[ProgressCallback],
) -> Optional[ProgressCallback]:
    """
    Wrap progress_cb to suppress consecutive calls with the same (percent, message).
    """
    if progress_cb is None:
        return None
    last_reported: Optional[Tuple[int, str]] = None

    def _wrapped(percent: int, message: str) -> None:
        nonlocal last_reported
        current = (percent, message)
        if current == last_reported:
            return
        last_reported = current
        progress_cb(percent, message)

    return _wrapped


@dataclass(frozen=True)
class TableDumpConfig:
    """
    Per-table configuration for technical dump/import in FK dependency order.

    ``col_offsets`` maps column names to remapping behavior when importing into a
    different ``target_project_id``:
      - ``None``: replace ``source_project_id`` with ``target_project_id``
      - ``int``: shift ID by ``(target_project_id - source_project_id) * offset``
    """

    model: Any
    col_offsets: Mapping[str, Optional[int]] = field(default_factory=dict)
    conflict_tolerant: bool = False
    regenerate_pk: Optional[Tuple[str, Optional[str]]] = None

    @property
    def table_name(self) -> str:
        return self.model.__tablename__


# Ordered in FK dependency order (must match TechnicalDump._table_queries).
TABLE_DUMP_CONFIGS: Tuple[TableDumpConfig, ...] = (
    TableDumpConfig(Instrument, conflict_tolerant=True),
    TableDumpConfig(Organization, conflict_tolerant=True),
    TableDumpConfig(User, conflict_tolerant=True),
    TableDumpConfig(Taxonomy, conflict_tolerant=True),
    TableDumpConfig(Collection, conflict_tolerant=True),
    TableDumpConfig(Project, col_offsets={"projid": None}),
    TableDumpConfig(
        ProjectPrivilege,
        col_offsets={"projid": None},
        regenerate_pk=(ProjectPrivilege.id.name, "nextval('seq_projectspriv')"),
    ),
    TableDumpConfig(ProjectTaxoStat, col_offsets={"projid": None}),
    TableDumpConfig(ProjectVariables, col_offsets={"project_id": None}),
    TableDumpConfig(
        TaxoRecast,
        col_offsets={"project_id": None},
        regenerate_pk=(TaxoRecast.recast_id.name, None),
    ),
    TableDumpConfig(CollectionProject, col_offsets={"project_id": None}),
    TableDumpConfig(UserPreferences, col_offsets={"project_id": None}),
    TableDumpConfig(
        Training,
        col_offsets={"projid": None},
        conflict_tolerant=True,
    ),
    TableDumpConfig(
        Sample,
        col_offsets={"projid": None, "sampleid": SAM_PRJ_OFFSET},
    ),
    TableDumpConfig(
        Acquisition,
        col_offsets={"acquisid": ACQ_PRJ_OFFSET, "acq_sample_id": SAM_PRJ_OFFSET},
    ),
    TableDumpConfig(Process, col_offsets={"processid": ACQ_PRJ_OFFSET}),
    TableDumpConfig(
        ObjectHeader,
        col_offsets={"objid": OBJ_PRJ_OFFSET, "acquisid": ACQ_PRJ_OFFSET},
    ),
    TableDumpConfig(
        ObjectFields,
        col_offsets={"objfid": OBJ_PRJ_OFFSET, "acquis_id": ACQ_PRJ_OFFSET},
    ),
    TableDumpConfig(
        Image,
        col_offsets={
            "objid": OBJ_PRJ_OFFSET,
            # NOTE: imgid is intentionally not remapped when cloning to another project.
            # IF ON SAME INSTANCE, both projects will share the same imgid values
            # and physical vault/ files so deleting one project (or its images)
            # will become problematic (removing files still referenced by the other).
            # Also image_file has imgid as PK.
            # TODO: Remap imgid + vault paths on target_project_id import, or guard deletion.
        },
    ),
    TableDumpConfig(ImageFile),
    TableDumpConfig(ObjectsClassifHisto, col_offsets={"objid": OBJ_PRJ_OFFSET}),
    TableDumpConfig(ObjectCNNFeatureVector, col_offsets={"objcnnid": OBJ_PRJ_OFFSET}),
    TableDumpConfig(Prediction, col_offsets={"object_id": OBJ_PRJ_OFFSET}),
    TableDumpConfig(PredictionHisto, col_offsets={"object_id": OBJ_PRJ_OFFSET}),
)
