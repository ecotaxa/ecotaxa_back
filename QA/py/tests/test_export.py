import datetime
import logging
import os
from io import BytesIO, TextIOWrapper
from unittest import mock
from zipfile import ZipFile

# noinspection PyPackageRequirements
from starlette import status

from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID, CREATOR_AUTH
from tests.test_classification import OBJECT_SET_CLASSIFY_URL
from tests.test_export_emodnet import JOB_DOWNLOAD_URL, JOB_LOG_DOWNLOAD_URL, add_concentration_data
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import SHARED_DIR, create_project, do_import, DATA_DIR, dump_project
from tests.test_jobs import get_job_and_wait_until_ok, wait_for_stable, api_check_job_ok, JOB_QUERY_URL
from tests.test_objectset_query import _prj_query

OBJECT_SET_EXPORT_URL = "/object_set/export"

EXPORT_ROOT_REF_DIR = "ref_exports"

_req_tmpl = {
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

formulae = {"SubSamplingCoefficient": "1/ssm.sub_part",
            "VolWBodySamp": "sam.tot_vol",  # Volumes are in m3 already for this data
            "IndividualBioVol": "4.0/3.0*math.pi*(math.sqrt(obj.area/math.pi)*ssm.pixel_size)**3"}


def test_export_sci(config, database, fastapi, caplog):
    caplog.set_level(logging.FATAL)

    # Admin imports the project, which is an export expected result
    from tests.test_import import test_import
    path = str(DATA_DIR / "ref_exports" / "bak_all_images")
    prj_id = test_import(config, database, caplog, "TSV sci export", path=path)

    # Validate all, otherwise empty report
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]  # Keep current
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={"target_ids": obj_ids,
                                                      "classifications": classifications,
                                                      "wanted_qualification": "V"})
    assert rsp.status_code == status.HTTP_200_OK

    # Abundance export whole project
    filters = {}
    req = _req_tmpl.copy()
    req.update({"project_id": prj_id,
                "exp_type": "ABO",
                "sum_subtotal": ""})
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_whole_project", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Abundance export by sample
    filters = {}
    req = _req_tmpl.copy()
    req.update({"project_id": prj_id,
                "exp_type": "ABO",
                "sum_subtotal": "S"})
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_by_sample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Abundance export by subsample
    filters = {}
    req = _req_tmpl.copy()
    req.update({"project_id": prj_id,
                "exp_type": "ABO",
                "sum_subtotal": "A"})
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_by_subsample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Abundance export by subsample but playing with taxa mapping
    filters = {}
    req = _req_tmpl.copy()
    req.update({"project_id": prj_id,
                "exp_type": "ABO",
                "sum_subtotal": "A",
                "pre_mapping": {85012: None,  # t001 -> Remove
                                84963: None,  # detritus -> Remove
                                85078: 78418,  # egg<other -> Oncaeidae
                                }})
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_by_subsample_mapped", only_hdr=True)
    # log = get_log_file(fastapi, job_id)


def test_export_cnc_biovol(config, database, fastapi, caplog):
    """ Specific test for concentrations and biovolume """
    # Admin imports the project
    from tests.test_import import test_import, test_import_a_bit_more_skipping, WEIRD_DIR
    prj_id = test_import(config, database, caplog, "SCISUM project")
    # Add a sample spanning 2 days
    test_import_a_bit_more_skipping(config, database, caplog, "SCISUM project")
    # Add some data for calculations
    add_concentration_data(fastapi, prj_id)
    # Add a sample with weird data in free columns
    do_import(prj_id, WEIRD_DIR, ADMIN_USER_ID)
    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    prj_json = rsp.json()
    # Validate everything, otherwise no export.
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 15
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]  # Keep current
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json={"target_ids": obj_ids,
                                                      "classifications": classifications,
                                                      "wanted_qualification": "V"})
    assert rsp.status_code == status.HTTP_200_OK

    # Concentrations export by sample
    filters = {}
    req = _req_tmpl.copy()
    req.update({"project_id": prj_id,
                "exp_type": "CNC",
                "sum_subtotal": "S",
                "formulae": formulae})
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "concentrations_by_sample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)


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
    filters = {}
    req = _req_tmpl.copy()
    req.update({"project_id": prj_id})
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

    # Backup export without images (but their ref is still in the TSVs)
    req.update({"exp_type": "BAK",
                "with_images": False,
                "only_first_image": False})
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_unzip_and_check(fastapi, job_id, "bak_no_image")

    # DOI export
    req.update({"exp_type": "DOI"})
    fixed_date = datetime.datetime(2021, 5, 30, 11, 22, 33)
    with mock.patch('helpers.DateTime._now_time',
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

    # Summary export, 3 types
    req.update({"exp_type": "SUM",
                "out_to_ftp": True,
                "sum_subtotal": "S"
                })
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_per_sample", only_hdr=True)

    req.update({"exp_type": "SUM",
                "out_to_ftp": True,
                "sum_subtotal": "A"
                })
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_per_subsample", only_hdr=True)

    req.update({"exp_type": "SUM",
                "out_to_ftp": True,
                "sum_subtotal": ""
                })
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "summary_whole", only_hdr=True)


def download_and_check(fastapi, job_id, ref_dir, only_hdr: bool = False):
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    tsv_check(rsp.content, ref_dir, only_hdr)


def download_and_unzip_and_check(fastapi, job_id, ref_dir, only_hdr: bool = False):
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    unzip_and_check(rsp.content, ref_dir, only_hdr)


def get_log_file(fastapi, job_id):
    log_url = JOB_LOG_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(log_url, headers=ADMIN_AUTH)
    return rsp.content


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
        if name.endswith(".log"):
            continue
        assert name in ref_dir_content
        ref_dir_content.remove(name)
        with zip_file.open(name) as myfile:
            content_bin = myfile.read()
        if name.endswith(".tsv"):
            one_tsv_check(content_bin, name, only_hdr, ref_dir_path)
    assert len(ref_dir_content) == 0


def one_tsv_check(content_bin, name, only_hdr, ref_dir_path):
    file_content = TextIOWrapper(BytesIO(content_bin), "utf-8-sig").readlines()
    print("".join(file_content))
    ref_content = open(ref_dir_path / name).readlines()
    assert len(file_content) == len(ref_content), "For %s, not same number of lines" % name
    num_line = 1
    for act, ref in zip(file_content, ref_content):
        assert act == ref, "diff in %s/%s line %d" % (ref_dir_path, name, num_line)
        if only_hdr:
            break
        num_line += 1


def test_export_roundtrip(config, database, fastapi, caplog):
    """ roundtrip export/import/compare"""
    caplog.set_level(logging.FATAL)

    # Admin imports the project
    from tests.test_import import test_import_uvp6
    prj_id = test_import_uvp6(config, database, caplog, "TSV UVP6 roundtrip export source project")

    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    _prj_json = rsp.json()

    # Admin exports it
    url = OBJECT_SET_EXPORT_URL
    req = {"project_id": prj_id,
           "exp_type": "BAK",
           "tsv_entities": "OPASHC",
           "coma_as_separator": False,
           "format_dates_times": True,
           "with_images": True,
           "only_first_image": False,
           "split_by": "sample",
           "with_internal_ids": False,
           "out_to_ftp": True,
           "sum_subtotal": ""}
    filters = {}
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK

    job_id = rsp.json()["job_id"]
    wait_for_stable(job_id)
    api_check_job_ok(fastapi, job_id)
    url = JOB_QUERY_URL.format(job_id=job_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    job_dict = rsp.json()
    file_in_ftp = job_dict["result"]["out_file"]

    # Create a clone project
    clone_prj_id = create_project(ADMIN_USER_ID, "TSV UVP6 roundtrip export clone project")
    do_import(clone_prj_id,
              source_path=DATA_DIR / "ftp" / ("task_%d_%s" % (job_id, file_in_ftp)), user_id=ADMIN_USER_ID)

    # TODO: Automate diff
    with open('exp_source.json', "w") as fd:
        dump_project(ADMIN_USER_ID, prj_id, fd)
    with open('exp_clone.json', "w") as fd:
        dump_project(ADMIN_USER_ID, clone_prj_id, fd)
