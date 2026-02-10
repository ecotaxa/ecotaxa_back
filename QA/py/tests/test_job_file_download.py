import pytest
from API_operations.helpers.JobService import JobServiceBase, ArgsDict
from export_shared import JOB_DOWNLOAD_URL
from tests.credentials import ADMIN_USER_ID, ADMIN_AUTH
from tests.jobs import api_wait_for_stable_job


# A job that produces a file
class FileProducingJob(JobServiceBase):
    JOB_TYPE = "FileProducing"
    PRODUCED_FILE_NAME = "test_output.txt"
    TEST_CONTENT = b"A" * 1024 + b"B" * 1024 + b"C" * 1024  # 3072 bytes

    def run(self, current_user_id: int) -> int:
        # Create pending job in DB
        return self.create_job(self.JOB_TYPE, current_user_id)

    def init_args(self, args: ArgsDict) -> ArgsDict:
        return args

    def do_background(self) -> None:
        # The job creates its own file
        file_path = (
            self.temp_for_jobs.base_dir_for(self.job_id) / self.PRODUCED_FILE_NAME
        )
        with open(file_path, "wb") as f:
            f.write(self.TEST_CONTENT)
        self.set_job_result(errors=[], infos={"file_created": True})


def test_get_job_file(fastapi, database):
    file_name = FileProducingJob.PRODUCED_FILE_NAME
    test_content = FileProducingJob.TEST_CONTENT

    # 1. Create and launch the job
    with FileProducingJob() as job:
        job.run(ADMIN_USER_ID)
        job_id = job.job_id
    assert job_id is not None

    job_dict = api_wait_for_stable_job(fastapi, job_id)
    assert job_dict["state"] == "F", job_dict

    download_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(download_url, headers=ADMIN_AUTH)

    assert rsp.status_code == 200
    assert rsp.content == test_content
    assert rsp.headers["content-disposition"] == f'attachment; filename="{file_name}"'
    assert rsp.headers["content-length"] == str(len(test_content))
    assert rsp.headers["accept-ranges"] == "bytes"

    # Full file with range 0- (same as 200 but with 206)
    rsp_p1 = fastapi.get(download_url, headers={**ADMIN_AUTH, "Range": "bytes=0-"})
    assert rsp_p1.status_code == 206
    assert rsp_p1.content == test_content
    assert rsp_p1.headers["content-length"] == str(len(test_content))
    assert (
        rsp_p1.headers["content-range"]
        == f"bytes 0-{len(test_content)-1}/{len(test_content)}"
    )

    # Part 2: Middle to end
    rsp_p2 = fastapi.get(download_url, headers={**ADMIN_AUTH, "Range": "bytes=1024-"})
    assert rsp_p2.status_code == 206
    assert rsp_p2.content == test_content[1024:]
    assert rsp_p2.headers["content-length"] == str(len(test_content) - 1024)
    assert (
        rsp_p2.headers["content-range"]
        == f"bytes 1024-{len(test_content)-1}/{len(test_content)}"
    )


def test_get_job_file_invalid_range(fastapi, database):
    with FileProducingJob() as job:
        job.run(ADMIN_USER_ID)
        job_id = job.job_id
    assert job_id is not None
    job_dict = api_wait_for_stable_job(fastapi, job_id)
    print(job_dict)
    assert job_dict["state"] == "F", job_dict

    download_url = JOB_DOWNLOAD_URL.format(job_id=job_id)

    # Invalid format
    rsp = fastapi.get(download_url, headers={**ADMIN_AUTH, "Range": "bytes=abc-"})
    assert rsp.status_code == 416

    # Out of bounds
    rsp = fastapi.get(download_url, headers={**ADMIN_AUTH, "Range": "bytes=5000-"})
    assert rsp.status_code == 416

    # Start > End
    rsp = fastapi.get(download_url, headers={**ADMIN_AUTH, "Range": "bytes=100-50"})
    assert rsp.status_code == 416

    # Multiple ranges (not supported)
    rsp = fastapi.get(download_url, headers={**ADMIN_AUTH, "Range": "bytes=0-10,20-30"})
    assert rsp.status_code == 416
