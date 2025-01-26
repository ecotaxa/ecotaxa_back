import json
import time
from typing import List, Dict

from API_operations.CRUD.Jobs import JobCRUDService
from BG_operations.JobScheduler import JobScheduler
from DB.Job import DBJobStateEnum
from sqlalchemy import text

from tests.credentials import ADMIN_USER_ID, ADMIN_AUTH

JOB_QUERY_URL = "/jobs/{job_id}/"
JOB_REPLY_URL = "/jobs/{job_id}/answer"

JOB_STABLE_STATES = (
    DBJobStateEnum.Finished,
    DBJobStateEnum.Asking,
    DBJobStateEnum.Error,
)


def wait_for_stable(job_id: int):
    """Wait for the job to be in a stable state, i.e. not running"""
    sched = False
    if not JobScheduler.do_run.is_set():
        # If we have _only_ a dependency on database, launch a scheduler, as the default one from fastapi is not present
        sched = True
        JobScheduler.launch_at_interval(0.01)
    with JobCRUDService() as sce:
        job = sce.query(ADMIN_USER_ID, job_id)
        while job.state not in JOB_STABLE_STATES:
            # This is ORM query so you need a fresh session for cross-session read
            sce.ro_session.expire_all()
            job = sce.query(ADMIN_USER_ID, job_id)
            time.sleep(0.01)
    if sched:
        JobScheduler.shutdown()
    return job


def check_job_ok(job):
    if job.state != DBJobStateEnum.Finished:
        if job.state == DBJobStateEnum.Asking:
            print("? " + str(job.question))
        else:
            print("NOT OK" + str(job.messages))
    assert (job.state, job.progress_pct, job.progress_msg) == (
        DBJobStateEnum.Finished,
        100,
        "Done",
    ), "Actual:" + str((job.state, job.progress_pct, job.progress_msg))


def check_job_errors(job) -> List[str]:
    assert job.state == DBJobStateEnum.Error, "Job is _not_ failed:%s" % [
        job.state,
        job.progress_pct,
        job.progress_msg,
        job.question,
    ]
    return json.loads(job.messages)


def get_job_errors(job) -> List[str]:
    msgs = json.loads(job.messages)
    return msgs


def api_wait_for_stable_job(fastapi, job_id, max_wait=20):
    url = JOB_QUERY_URL.format(job_id=job_id)
    waited = 0
    while True:
        rsp = fastapi.get(url, headers=ADMIN_AUTH)
        job_dict = rsp.json()
        if job_dict["state"] in JOB_STABLE_STATES:
            return job_dict
        time.sleep(0.1)
        waited += 1
        if waited > max_wait:
            assert False, "Waited too long, job: %s" + str(job_dict)


def api_reply_to_waiting_job(fastapi, job_id, reply):
    url = JOB_REPLY_URL.format(job_id=job_id)
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=reply)
    assert rsp.status_code == 200


def api_check_job_ok(fastapi, job_id):
    url = JOB_QUERY_URL.format(job_id=job_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    job_dict = rsp.json()
    if (job_dict["state"], job_dict["progress_pct"], job_dict["progress_msg"]) == (
        "F",
        100,
        "Done",
    ):
        pass
    else:
        assert "Job failed", str(job_dict)
    return job_dict


def api_check_job_errors(fastapi, job_id) -> List[str]:
    url = JOB_QUERY_URL.format(job_id=job_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    job_dict = rsp.json()
    print(job_dict)
    assert job_dict["state"] == DBJobStateEnum.Error
    return job_dict["errors"]


def api_check_job_questions(fastapi, job_id) -> Dict:
    url = JOB_QUERY_URL.format(job_id=job_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    job_dict = rsp.json()
    assert job_dict["state"] == DBJobStateEnum.Asking
    return job_dict["question"]


def api_check_job_failed(fastapi, job_id, expected_message):
    url = JOB_QUERY_URL.format(job_id=job_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    job_dict = rsp.json()
    assert (job_dict["state"], job_dict["progress_msg"]) == ("E", expected_message)
    return rsp


def get_job_and_wait_until_ok(fastapi, rsp):
    job_id = rsp.json()["job_id"]
    wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    return job_id


def clear_all_jobs():
    with JobCRUDService() as sce:
        sce.session.execute(text("DELETE FROM job"))
        sce.session.commit()
