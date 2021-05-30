import json
import time
from typing import List, Dict

from API_operations.CRUD.Jobs import JobCRUDService
from BG_operations.JobScheduler import JobScheduler
from DB.Job import DBJobStateEnum

from tests.credentials import ADMIN_USER_ID, ADMIN_AUTH

JOB_QUERY_URL = "/jobs/{job_id}/"
FILE_IMPORT_URL = "/file_import/{project_id}"


def wait_for_stable(job_id: int):
    """ Wait for the job to be in a stable state, i.e. not running """
    with JobCRUDService() as sce:
        assert sce.query(ADMIN_USER_ID, job_id).state == DBJobStateEnum.Pending
        with JobScheduler() as jsce:
            jsce.run_one()
            jsce.wait_for_stable()
        return sce.query(ADMIN_USER_ID, job_id)


def check_job_ok(job):
    if job.state != DBJobStateEnum.Finished:
        if job.state == DBJobStateEnum.Asking:
            print("? " + job.question)
        else:
            print("NOT OK" + job.messages)
    assert (job.state, job.progress_pct, job.progress_msg) == (DBJobStateEnum.Finished, 100, "Done")


def check_job_errors(job) -> List[str]:
    assert job.state == DBJobStateEnum.Error, "Job is :%s" % [job.state, job.progress_pct, job.progress_msg,
                                                              job.question]
    return json.loads(job.messages)


def get_job_errors(job) -> List[str]:
    msgs = json.loads(job.messages)
    return msgs


def api_wait_for_stable_job(fastapi, job_id):
    url = JOB_QUERY_URL.format(job_id=job_id)
    waited = 0
    while True:
        rsp = fastapi.get(url, headers=ADMIN_AUTH)
        job_dict = rsp.json()
        if job_dict["state"] in ('F', 'A', 'E'):
            return job_dict
        time.sleep(0.1)
        waited += 1
        if waited > 20:
            assert False, "Waited too long, job: %s" + str(job_dict)


def api_check_job_ok(fastapi, job_id):
    url = JOB_QUERY_URL.format(job_id=job_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    job_dict = rsp.json()
    assert (job_dict["state"], job_dict["progress_pct"], job_dict["progress_msg"]) == ('F', 100, 'Done')


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
    assert (job_dict["state"], job_dict["progress_msg"]) == ('E', expected_message)


def get_job_and_wait_until_ok(fastapi, rsp):
    job_id = rsp.json()["job_id"]
    wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    return job_id
