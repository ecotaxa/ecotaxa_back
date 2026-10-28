import pytest

from API_operations.helpers.JobService import JobServiceBase, ArgsDict
from API_operations.helpers.Service import Service
from BG_operations.JobScheduler import JobScheduler
from DB.Job import Job, DBJobStateEnum
from tests.credentials import ADMIN_USER_ID, CREATOR_USER_ID
from tests.jobs import clear_all_jobs


class QuotaJob(JobServiceBase):
    JOB_TYPE = "QuotaJob"

    def run(self, current_user_id: int) -> None:
        self.create_job(self.JOB_TYPE, current_user_id)

    def init_args(self, args: ArgsDict) -> ArgsDict:
        return args

    def do_background(self) -> None:
        self.set_job_result(errors=[], infos={})


class OtherQuotaJob(QuotaJob):
    JOB_TYPE = "OtherQuotaJob"


def _create_job(job_class, user_id: int) -> int:
    with job_class() as job:
        job.run(user_id)
        return job.job_id


def _set_state(job_id: int, state: DBJobStateEnum) -> None:
    with Service() as sce:
        job = sce.session.get(Job, job_id)
        assert job is not None
        job.state = state
        sce.session.commit()


@pytest.fixture
def stopped_scheduler(fastapi):
    """
    Keep the background scheduler out of the way, so that tests control which job
    is picked, and leave a clean job table behind.
    """
    JobScheduler.shutdown()
    clear_all_jobs()
    yield
    clear_all_jobs()
    import main

    JobScheduler.launch_at_interval(main.JOB_INTERVAL)


@pytest.mark.parametrize(
    "active_state", [DBJobStateEnum.Running, DBJobStateEnum.Asking]
)
def test_no_second_active_job_of_same_type_for_user(
    fastapi, stopped_scheduler, active_state
):
    active_id = _create_job(QuotaJob, ADMIN_USER_ID)
    pending_id = _create_job(QuotaJob, ADMIN_USER_ID)
    _set_state(active_id, active_state)

    # The pending job must wait for the active one to finish
    with JobScheduler() as scheduler:
        assert scheduler._pick_pending_job() is None

    # Once the slot is free, the pending job becomes eligible
    _set_state(active_id, DBJobStateEnum.Finished)
    with JobScheduler() as scheduler:
        picked = scheduler._pick_pending_job()
        assert picked is not None
        assert picked.id == pending_id


def test_limit_is_per_user_and_per_type(fastapi, stopped_scheduler):
    active_id = _create_job(QuotaJob, ADMIN_USER_ID)
    blocked_id = _create_job(QuotaJob, ADMIN_USER_ID)
    other_user_id = _create_job(QuotaJob, CREATOR_USER_ID)
    other_type_id = _create_job(OtherQuotaJob, ADMIN_USER_ID)
    _set_state(active_id, DBJobStateEnum.Running)

    # Same type but another user is not blocked
    with JobScheduler() as scheduler:
        picked = scheduler._pick_pending_job()
        assert picked is not None
        assert picked.id == other_user_id

    # Another job type for the same user is not blocked either
    _set_state(other_user_id, DBJobStateEnum.Finished)
    with JobScheduler() as scheduler:
        picked = scheduler._pick_pending_job()
        assert picked is not None
        assert picked.id == other_type_id

    # The blocked job becomes eligible once the active one is finished
    _set_state(other_type_id, DBJobStateEnum.Finished)
    _set_state(active_id, DBJobStateEnum.Finished)
    with JobScheduler() as scheduler:
        picked = scheduler._pick_pending_job()
        assert picked is not None
        assert picked.id == blocked_id


def test_new_job_supersedes_older_asking_job(fastapi, stopped_scheduler):
    asking_id = _create_job(QuotaJob, ADMIN_USER_ID)
    other_type_asking_id = _create_job(OtherQuotaJob, ADMIN_USER_ID)
    other_user_asking_id = _create_job(QuotaJob, CREATOR_USER_ID)
    _set_state(asking_id, DBJobStateEnum.Asking)
    _set_state(other_type_asking_id, DBJobStateEnum.Asking)
    _set_state(other_user_asking_id, DBJobStateEnum.Asking)

    new_id = _create_job(QuotaJob, ADMIN_USER_ID)

    with Service() as sce:
        old_job = sce.session.get(Job, asking_id)
        assert old_job.state == DBJobStateEnum.Error
        assert old_job.progress_msg == f"Superseded by job #{new_id}"
        # Only jobs of the same user and type are superseded
        assert (
            sce.session.get(Job, other_type_asking_id).state
            == DBJobStateEnum.Asking
        )
        assert (
            sce.session.get(Job, other_user_asking_id).state
            == DBJobStateEnum.Asking
        )
        assert sce.session.get(Job, new_id).state == DBJobStateEnum.Pending

    # The new job is not blocked by the abandoned asking job anymore
    with JobScheduler() as scheduler:
        picked = scheduler._pick_pending_job()
        assert picked is not None
        assert picked.id == new_id
