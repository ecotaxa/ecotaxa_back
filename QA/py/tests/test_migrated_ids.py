# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from starlette import status
from DB.MigratedIDs import ObjidOld2New, SampleIdOld2New, AcquisIdOld2New
from API_operations.helpers.Service import Service


def test_migrated_ids_empty(fastapi):
    # Test with no parameters
    rsp = fastapi.get("/migrated_ids")
    assert rsp.status_code == status.HTTP_200_OK
    data = rsp.json()
    assert data == {"objects": {}, "samples": {}, "acquisitions": {}, "projects": {}}


def test_migrated_ids_with_data(fastapi):
    # Add some data to the database
    # Realistic IDs are based on project offsets:
    # OBJ_PRJ_OFFSET = 100_000_000
    # SAM_PRJ_OFFSET = 1_000_000
    # ACQ_PRJ_OFFSET = 10_000_000
    # For a project with ID 1:
    # Objects start at 100,000,001
    # Samples start at 1,000,001
    # Acquisitions start at 10,000,001
    with Service() as sce:
        # Objects
        sce.session.add(ObjidOld2New(old_id=101, new_id=100000201))
        sce.session.add(ObjidOld2New(old_id=102, new_id=100000202))
        # Samples
        sce.session.add(SampleIdOld2New(old_id=301, new_id=1000401))
        # Acquisitions
        sce.session.add(AcquisIdOld2New(old_id=501, new_id=10000601))
        sce.session.commit()

    try:
        # Test individual categories
        # Objects
        rsp = fastapi.get("/migrated_ids", params={"objects": "101,102,103"})
        assert rsp.status_code == status.HTTP_200_OK
        data = rsp.json()
        assert data["objects"] == {"101": 100000201, "102": 100000202}
        assert "103" not in data["objects"]

        # Samples
        rsp = fastapi.get("/migrated_ids", params={"samples": "301,302"})
        assert rsp.status_code == status.HTTP_200_OK
        data = rsp.json()
        assert data["samples"] == {"301": 1000401}

        # Acquisitions
        rsp = fastapi.get("/migrated_ids", params={"acquisitions": "501"})
        assert rsp.status_code == status.HTTP_200_OK
        data = rsp.json()
        assert data["acquisitions"] == {"501": 10000601}

        # Mixed
        rsp = fastapi.get(
            "/migrated_ids",
            params={"objects": "101", "samples": "301", "acquisitions": "501"},
        )
        assert rsp.status_code == status.HTTP_200_OK
        data = rsp.json()
        assert data["objects"] == {"101": 100000201}
        assert data["samples"] == {"301": 1000401}
        assert data["acquisitions"] == {"501": 10000601}

        # Test with non-numeric separators (as per doc)
        # The first non-digit character is used as separator.
        # In "101;102;103", ';' is the separator.
        rsp = fastapi.get("/migrated_ids", params={"objects": "101;102;103"})
        assert rsp.status_code == status.HTTP_200_OK
        data = rsp.json()
        assert data["objects"] == {"101": 100000201, "102": 100000202}

    finally:
        # Cleanup added data
        with Service() as sce:
            sce.session.query(ObjidOld2New).filter(
                ObjidOld2New.old_id.in_([101, 102])
            ).delete()
            sce.session.query(SampleIdOld2New).filter(
                SampleIdOld2New.old_id == 301
            ).delete()
            sce.session.query(AcquisIdOld2New).filter(
                AcquisIdOld2New.old_id == 501
            ).delete()
            sce.session.commit()
