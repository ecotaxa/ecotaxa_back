# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from unittest.mock import patch

import pytest
from sqlalchemy import select

from API_operations.CRUD.Jobs import JobCRUDService
from API_operations.helpers.Service import Service
from BO.Job import JobBO
from BO.Rights import NOT_AUTHORIZED, NOT_FOUND
from DB.Job import DBJobStateEnum, Job
from tests.credentials import ADMIN_USER_ID, CREATOR_USER_ID, ORDINARY_USER_USER_ID
from tests.jobs import clear_all_jobs


@pytest.fixture(autouse=True)
def _cleanup_jobs(database):
    clear_all_jobs()
    yield
    clear_all_jobs()


def _create_test_job(
    owner_id: int, state: DBJobStateEnum = DBJobStateEnum.Pending
) -> int:
    with JobCRUDService() as sce:
        job = JobBO.create_job(owner_id, "TestJobType", {"k": "v"})
        job.state = state
        job.progress_msg = "initial_msg"
        sce.session.add(job)
        sce.session.commit()
        return job.id


def test_job_bo_exit_rolls_back_on_exception(database):
    clear_all_jobs()
    job_id = _create_test_job(ADMIN_USER_ID)

    with Service() as sce:
        with pytest.raises(RuntimeError, match="boom"):
            with JobBO.get_for_update(sce.session, job_id) as job_bo:
                job_bo.progress_msg = "should_not_commit"
                raise RuntimeError("boom")

        assert job_bo._session is None

        # Row lock must have been released by rollback() even before outer Service exits
        with Service() as sce2:
            locked = sce2.session.execute(
                select(Job).where(Job.id == job_id).with_for_update(nowait=True)
            ).scalar_one()
            assert locked.progress_msg == "initial_msg"
            sce2.session.rollback()


def test_job_bo_exit_clears_session_when_commit_fails(database):
    clear_all_jobs()
    job_id = _create_test_job(ADMIN_USER_ID)

    with Service() as sce:
        with patch.object(
            sce.session, "commit", side_effect=RuntimeError("commit failed")
        ):
            with pytest.raises(RuntimeError, match="commit failed"):
                with JobBO.get_for_update(sce.session, job_id) as job_bo:
                    job_bo.progress_msg = "updated"

        assert job_bo._session is None
        sce.session.rollback()


def test_query_for_update_unauthorized_does_not_lock_or_leak_session(database):
    clear_all_jobs()
    job_id = _create_test_job(ADMIN_USER_ID, state=DBJobStateEnum.Error)

    with JobCRUDService() as sce:
        with pytest.raises(AssertionError, match=NOT_AUTHORIZED):
            sce.restart(ORDINARY_USER_USER_ID, job_id)

        # Must not have dirtied the RW session or acquired a FOR UPDATE lock
        assert not sce.session.dirty
        with Service() as sce2:
            locked = sce2.session.execute(
                select(Job).where(Job.id == job_id).with_for_update(nowait=True)
            ).scalar_one()
            assert locked.state == DBJobStateEnum.Error
            sce2.session.rollback()


def test_query_for_update_missing_job_does_not_leak(database):
    clear_all_jobs()

    with JobCRUDService() as sce:
        with pytest.raises(AssertionError, match=NOT_FOUND):
            sce._query_for_update(ADMIN_USER_ID, 999999999)
        assert not sce.session.dirty


def test_query_for_update_authorized_still_works(database):
    clear_all_jobs()
    job_id = _create_test_job(CREATOR_USER_ID, state=DBJobStateEnum.Error)

    with JobCRUDService() as sce:
        sce.restart(CREATOR_USER_ID, job_id)

    with JobCRUDService() as sce:
        job_bo = sce.query(ADMIN_USER_ID, job_id)
        assert job_bo.state == DBJobStateEnum.Pending
        assert job_bo.progress_msg == JobBO.RESTARTING_MESSAGE
