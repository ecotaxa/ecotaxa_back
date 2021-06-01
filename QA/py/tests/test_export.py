import datetime
import logging
import os
from io import BytesIO, TextIOWrapper
from unittest import mock
from zipfile import ZipFile

# noinspection PyPackageRequirements
from starlette import status

from tests.credentials import ADMIN_AUTH
from tests.test_export_emodnet import JOB_DOWNLOAD_URL
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import SHARED_DIR
from tests.test_jobs import get_job_and_wait_until_ok

OBJECT_SET_EXPORT_URL = "/object_set/export"

EXPORT_ROOT_REF_DIR = "ref_exports"


def test_export_tsv(config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping
    prj_id = test_import(config, database, caplog, "TSV export project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(config, database, caplog, "TSV export project")

    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    _prj_json = rsp.json()

    caplog.set_level(logging.DEBUG)

    # Admin exports it
    url = OBJECT_SET_EXPORT_URL
    req = {"project_id": prj_id,
           "exp_type": "TSV",
           "tsv_entities": "OPASHC",
           "coma_as_separator": False,
           "format_dates_times": False,
           "with_images": False,
           "only_first_image": False,
           "split_by": "sample",
           "with_internal_ids": False,
           "out_to_ftp": False,
           "sum_subtotal": ""}
    filters = {}
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "tsv_all_entities_no_img_no_ids")

    # Backup export
    req.update({"exp_type": "BAK",
                "with_images": True,
                "only_first_image": False})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "bak_all_images")

    # DOI export
    req.update({"exp_type": "DOI"})
    fixed_date = datetime.datetime(2021, 5, 30, 11, 22, 33)
    with mock.patch('helpers.DateTime.now_time',
                    return_value=fixed_date):
        rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
        assert rsp.status_code == status.HTTP_200_OK
        _job_id = get_job_and_wait_until_ok(fastapi, rsp)
    # The object_id inside prevents predictability
    # TODO: Better comparison ignoring columns, inject project id and so on
    # download_and_unzip_and_check(fastapi, job_id, "doi", only_hdr=True)

    # TSV export with IDs
    req.update({"exp_type": "TSV",
                "with_internal_ids": True,
                "out_to_ftp": True,
                "coma_as_separator": True})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    # Too much randomness inside: IDs, random value
    # TODO: Better comparison ignoring columns
    download_and_unzip_and_check(fastapi, job_id, "tsv_with_ids", only_hdr=True)

    # Summary export
    req.update({"exp_type": "SUM",
                "out_to_ftp": True,
                "sum_subtotal": "S"
                })
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    # Too much randomness inside: IDs, random value
    # TODO: Better comparison ignoring columns
    download_and_check(fastapi, job_id, "summary", only_hdr=True)


def download_and_check(fastapi, job_id, ref_dir, only_hdr: bool = False):
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    tsv_check(rsp.content, ref_dir, only_hdr)


def download_and_unzip_and_check(fastapi, job_id, ref_dir, only_hdr: bool = False):
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    unzip_and_check(rsp.content, ref_dir, only_hdr)


def tsv_check(tsv_content, ref_dir: str, only_hdr: bool):
    ref_dir_path = SHARED_DIR / EXPORT_ROOT_REF_DIR / ref_dir
    one_tsv_check(tsv_content, "ref.tsv", only_hdr=False, ref_dir_path=ref_dir_path)


def recursive_list_dir(pth: str):
    dir_list = [pth]
    files = []
    while len(dir_list) > 0:
        for (dirpath, dirnames, filenames) in os.walk(dir_list.pop()):
            dirpath = dirpath[len(pth) + 1:]
            dir_list.extend(dirnames)
            files.extend(map(lambda n: os.path.join(*n),
                             zip([dirpath] * len(filenames),
                                 filenames)))
    return files


def unzip_and_check(zip_content, ref_dir: str, only_hdr: bool):
    ref_dir_path = SHARED_DIR / EXPORT_ROOT_REF_DIR / ref_dir
    ref_dir_content = recursive_list_dir(str(ref_dir_path))

    pseudo_file = BytesIO(zip_content)
    zip_file = ZipFile(pseudo_file)
    for a_file in zip_file.filelist:
        name = a_file.filename
        assert name in ref_dir_content
        # ref_dir_content.remove(name)
        with zip_file.open(name) as myfile:
            content_bin = myfile.read()
        if name.endswith(".tsv"):
            one_tsv_check(content_bin, name, only_hdr, ref_dir_path)
    # assert len(ref_dir_content) == 0


def one_tsv_check(content_bin, name, only_hdr, ref_dir_path):
    file_content = TextIOWrapper(BytesIO(content_bin), "utf-8").readlines()
    ref_content = open(ref_dir_path / name).readlines()
    assert len(file_content) == len(ref_content), "For %s, not same number of lines" % name
    num_line = 1
    for act, ref in zip(file_content, ref_content):
        assert ref == act, "diff in %s line %d" % (name, num_line)
        if only_hdr:
            break
        num_line += 1
