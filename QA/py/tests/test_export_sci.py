import logging

from starlette import status

from tests.credentials import CREATOR_AUTH, ADMIN_AUTH, ADMIN_USER_ID
from tests.export_shared import download_and_check
from tests.test_classification import OBJECT_SET_CLASSIFY_URL
from tests.test_export import _req_tmpl, OBJECT_SET_EXPORT_URL
from tests.test_export_emodnet import add_concentration_data
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import DATA_DIR, do_import
from tests.test_jobs import get_job_and_wait_until_ok
from tests.test_objectset_query import _prj_query

formulae = {"SubSamplingCoefficient": "1/ssm.sub_part",
            "VolWBodySamp": "sam.tot_vol",  # Volumes are in m3 already for this data
            "IndividualBioVol": "4.0/3.0*math.pi*(math.sqrt(obj.area/math.pi)*ssm.pixel)**3"}


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


def test_export_conc_biovol(config, database, fastapi, caplog):
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

    # Biovolume export by sample
    filters = {}
    req = _req_tmpl.copy()
    req.update({"project_id": prj_id,
                "exp_type": "BIV",
                "sum_subtotal": "S",
                "formulae": formulae})
    req_and_filters = {"filters": filters,
                       "request": req}
    rsp = fastapi.post(OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "biovolumes_by_sample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Biovolume export by subsample AKA Acquisition
    req.update({"sum_subtotal": "A"})
    rsp = fastapi.post(OBJECT_SET_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters)
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "biovolumes_by_subsample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)
