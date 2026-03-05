import time
from types import SimpleNamespace
from typing import Union, List, Dict

from requests import Response
from starlette.testclient import TestClient

from tests.credentials import ADMIN_AUTH

from DB.Job import DBJobStateEnum

FILE_IMPORT_URL = "/file_import/{project_id}"
JOB_QUERY_URL = "/jobs/{job_id}/"

JOB_STABLE_STATES = (
    DBJobStateEnum.Finished,
    DBJobStateEnum.Asking,
    DBJobStateEnum.Error,
)


def api_file_import(
    fastapi: TestClient, prj_id: Union[int, str], req: dict, auth: dict
) -> Response:
    url = FILE_IMPORT_URL.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=auth, json=req)
    return rsp


def api_wait_for_stable_job(fastapi, job_id, max_wait=300):
    url = JOB_QUERY_URL.format(job_id=job_id)
    waited = 0
    while True:
        rsp = fastapi.get(url, headers=ADMIN_AUTH)
        job_dict = rsp.json()
        if job_dict["state"] in JOB_STABLE_STATES:
            ret = job_dict
            break
        time.sleep(0.02)
        waited += 1
        if waited > max_wait:
            assert False, "Waited too long, job: %s" + str(job_dict)
    return SimpleNamespace(**ret)  # Allow t["state"] and t.state


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
        assert False, "Job failed:" + str(job_dict)
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
    assert (job_dict["state"], job_dict["progress_msg"]) == (
        "E",
        expected_message,
    ), job_dict
    return rsp


MY_FILES_URL = "/user_files/"
REMOVE_FILE_URL = "/user_files/rm/"
MOVE_FILE_URL = "/user_files/mv/"
CREATE_FILE_URL = "/user_files/create/"


def api_upload_file(fastapi: TestClient, local_file: str, dest_path: str, auth: dict):
    with open(local_file, "rb") as fin:
        upload_rsp = fastapi.post(
            MY_FILES_URL,
            headers=auth,
            data={
                "path": dest_path
            },  # /!\ If no pathparam error-> random use-once directory!
            files={"file": fin},
        )
        assert upload_rsp.status_code == 200
        srv_file_path = upload_rsp.json()
        return srv_file_path


def api_move_user_file(
    fastapi: TestClient, source_path: str, dest_path: str, auth: dict
) -> Response:
    rsp = fastapi.post(
        MOVE_FILE_URL,
        headers=auth,
        data={"source_path": source_path, "dest_path": dest_path},
    )
    return rsp


def api_remove_user_file(fastapi: TestClient, source_path: str, auth: dict) -> Response:
    rsp = fastapi.post(REMOVE_FILE_URL, headers=auth, data={"source_path": source_path})
    return rsp


def api_create_user_file(fastapi: TestClient, source_path: str, auth: dict) -> Response:
    rsp = fastapi.post(CREATE_FILE_URL, headers=auth, data={"source_path": source_path})
    return rsp
