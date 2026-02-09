import pytest
from API_operations.helpers.JobService import JobServiceBase, ArgsDict
from tests.credentials import ADMIN_USER_ID, ADMIN_AUTH
from tests.jobs import api_wait_for_stable_job, clear_all_jobs
from DB.Job import DBJobStateEnum


# We need some fake jobs to test filtering
class TypeAJob(JobServiceBase):
    JOB_TYPE = "TypeA"

    def run(self, current_user_id: int) -> int:
        return self.create_job(self.JOB_TYPE, current_user_id)

    def init_args(self, args: ArgsDict) -> ArgsDict:
        return args

    def do_background(self) -> None:
        self.set_job_result(errors=[], infos={})


class TypeBJob(JobServiceBase):
    JOB_TYPE = "TypeB"

    def run(self, current_user_id: int) -> int:
        return self.create_job(self.JOB_TYPE, current_user_id)

    def init_args(self, args: ArgsDict) -> ArgsDict:
        return args

    def do_background(self) -> None:
        # Simulate an error for some jobs
        raise Exception("Simulated error")


def test_list_jobs_filtering(fastapi, database):
    # Register our test job classes if needed, though JobServiceBase.create_job works anyway

    # 0. Cleanup
    clear_all_jobs()

    # 1. Create some jobs of different types and that will end in different states
    # TypeA -> Finished
    with TypeAJob() as job1:
        job1.run(ADMIN_USER_ID)
        id1 = job1.job_id

    # Another TypeA -> Finished
    with TypeAJob() as job2:
        job2.run(ADMIN_USER_ID)
        id2 = job2.job_id

    # TypeB -> Error
    with TypeBJob() as job3:
        job3.run(ADMIN_USER_ID)
        id3 = job3.job_id

    # Wait for all jobs to be stable
    api_wait_for_stable_job(fastapi, id1)
    api_wait_for_stable_job(fastapi, id2)
    api_wait_for_stable_job(fastapi, id3)

    # 2. Test filtering by job_type
    rsp = fastapi.get("/jobs/?for_admin=true&job_type=TypeA", headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    jobs = rsp.json()
    assert len(jobs) == 2
    assert all(j["type"] == "TypeA" for j in jobs)
    assert {j["id"] for j in jobs} == {id1, id2}

    rsp = fastapi.get("/jobs/?for_admin=true&job_type=TypeB", headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    jobs = rsp.json()
    assert len(jobs) == 1
    assert jobs[0]["type"] == "TypeB"
    assert jobs[0]["id"] == id3

    # 3. Test filtering by job_status
    # Status 'F' is Finished
    rsp = fastapi.get(
        f"/jobs/?for_admin=true&job_status={DBJobStateEnum.Finished.value}",
        headers=ADMIN_AUTH,
    )
    assert rsp.status_code == 200
    jobs = rsp.json()
    assert len(jobs) == 2
    assert all(j["state"] == "F" for j in jobs)

    # Status 'E' is Error
    rsp = fastapi.get(
        f"/jobs/?for_admin=true&job_status={DBJobStateEnum.Error.value}",
        headers=ADMIN_AUTH,
    )
    assert rsp.status_code == 200
    jobs = rsp.json()
    assert len(jobs) == 1
    assert jobs[0]["state"] == "E"
    assert jobs[0]["id"] == id3

    # 4. Test filtering by both
    rsp = fastapi.get(
        f"/jobs/?for_admin=true&job_type=TypeA&job_status={DBJobStateEnum.Finished.value}",
        headers=ADMIN_AUTH,
    )
    assert rsp.status_code == 200
    jobs = rsp.json()
    assert len(jobs) == 2

    rsp = fastapi.get(
        f"/jobs/?for_admin=true&job_type=TypeA&job_status={DBJobStateEnum.Error.value}",
        headers=ADMIN_AUTH,
    )
    assert rsp.status_code == 200
    jobs = rsp.json()
    assert len(jobs) == 0

    # 5. Test with for_admin=false (should still work for owner)
    rsp = fastapi.get("/jobs/?for_admin=false&job_type=TypeA", headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    jobs = rsp.json()
    assert len(jobs) == 2
