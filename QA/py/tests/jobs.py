from typing import List

from API_operations.CRUD.Jobs import JobCRUDService
from DB.Job import DBJobStateEnum
from sqlalchemy import text

from tests.api_wrappers import api_wait_for_stable_job, api_check_job_ok
from tests.credentials import ADMIN_AUTH

JOB_REPLY_URL = "/jobs/{job_id}/answer"


def check_job_ok(job):
    if job.state != DBJobStateEnum.Finished:
        if job.state == DBJobStateEnum.Asking:
            print("? " + str(job.question))
        else:
            print("NOT OK" + str(job.errors))
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
    return job.errors


def api_reply_to_waiting_job(fastapi, job_id, reply):
    url = JOB_REPLY_URL.format(job_id=job_id)
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=reply)
    assert rsp.status_code == 200, rsp.text


def get_job_and_wait_until_ok(fastapi, rsp):
    job_id = rsp.json()["job_id"]
    api_wait_for_stable_job(fastapi, job_id)
    api_check_job_ok(fastapi, job_id)
    return job_id


def clear_all_jobs():
    with JobCRUDService() as sce:
        sce.session.execute(text("DELETE FROM job"))
        sce.session.commit()
