# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
import gc
import weakref

from API_operations.CRUD.Object import ObjectService
from API_operations.CRUD.ObjectParents import (
    SamplesService,
    AcquisitionsService,
    ProcessesService,
)
from API_operations.ObjectManager import ObjectManager
from tests.test_import import ADMIN_USER_ID, do_import_uvp6


def test_mapped_entity_does_not_retain_session(database, fastapi):
    prj_id, _ = do_import_uvp6(fastapi, "Test Session Lifecycle")

    with ObjectManager() as sce:
        qry_rsp, _details, _total = sce.query(ADMIN_USER_ID, prj_id, filters={})
    first_obj = qry_rsp[0]
    obj_id, acq_id, sam_id = first_obj[0], first_obj[1], first_obj[2]
    proc_id = acq_id

    for service_cls, entity_id in (
        (ObjectService, obj_id),
        (SamplesService, sam_id),
        (AcquisitionsService, acq_id),
        (ProcessesService, proc_id),
    ):
        with service_cls() as sce:
            rw_ref = weakref.ref(sce.session)
            ro_ref = weakref.ref(sce.ro_session)
            bo = sce.query(ADMIN_USER_ID, entity_id)
            assert bo is not None
            assert not hasattr(bo, "_session")
        del sce
        gc.collect()
        assert rw_ref() is None
        assert ro_ref() is None
        assert bo is not None
