import json
from typing import Dict, List
from starlette import status
from DB.TaxoRecast import RecastOperation
from tests.api_wrappers import api_wait_for_stable_job
from tests.credentials import CREATOR_AUTH, ADMIN_AUTH
from tests.export_shared import download_and_check, JOB_DOWNLOAD_URL
from tests.formulae import uvp_formulae
from tests.jobs import get_job_and_wait_until_ok, check_job_errors
from tests.test_classification import OBJECT_SET_CLASSIFY_URL
from tests.test_export_emodnet import add_concentration_data, PROJECT_SEARCH_SAMPLES_URL
from tests.test_fastapi import PROJECT_QUERY_URL
from tests.test_import import (
    DATA_DIR,
    do_import,
    do_test_import,
    do_import_a_bit_more_skipping,
)
from tests.test_objectset_query import _prj_query
from tests.test_update_prj import PROJECT_UPDATE_URL

OBJECT_SET_SUMMARY_EXPORT_URL = "/object_set/export/summary"
TAXORECAST_URL = "/taxo_recast"


def set_formulae_in_project(fastapi, prj_id: int, prj_formulae: Dict):
    read_url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(read_url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    prj_json = rsp.json()
    prj_json["formulae"] = json.dumps(prj_formulae)
    upd_url = PROJECT_UPDATE_URL.format(project_id=prj_id)
    rsp = fastapi.put(upd_url, headers=ADMIN_AUTH, json=prj_json)
    assert rsp.status_code == status.HTTP_200_OK


def test_export_abundances(fastapi):

    # Admin imports the project, which is an export expected result
    path = str(DATA_DIR / "ref_exports" / "bak_all_images")
    prj_id = do_test_import(fastapi, "TSV sci export", path=path)
    set_formulae_in_project(
        fastapi, prj_id, uvp_formulae
    )  # Note: This is _not_ needed for abundances

    # Validate all, otherwise empty report
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]  # Keep current
    rsp = fastapi.post(
        url,
        headers=ADMIN_AUTH,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK

    # Abundance export whole project
    req_and_filters = {
        "filters": {},
        "request": {"project_id": prj_id, "summarise_by": "none"},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_whole_project", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Abundance export by sample, default values everywhere
    req_and_filters = {"filters": {}, "request": {"project_id": prj_id}}
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_by_sample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Abundance export by subsample
    req_and_filters = {
        "filters": {},
        "request": {"project_id": prj_id, "summarise_by": "acquisition"},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_by_subsample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)
    # add recast in taxo_recast
    recast = {
        "from_to": {
            "85012": 0,  # t001 -> Remove
            "84963": 0,  # detritus -> Remove
            "85078": 78418,  # egg<other -> Oncaeidae
            "92731": 78418,  # small<egg -> Oncaeidae
        },
        "doc": {},
    }
    recastreq = {
        "target_id": prj_id,
        "operation": RecastOperation.project_export.value,
        "recast": recast,
        "is_collection": False,
    }
    rsp = fastapi.put(TAXORECAST_URL, json=recastreq, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    # Abundance export by subsample but playing with taxa mapping
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "summarise_by": "acquisition",
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "abundances_by_subsample_mapped", only_hdr=True)
    # log = get_log_file(fastapi, job_id)


def test_export_conc_biovol(fastapi):
    """Specific test for concentrations and biovolume"""
    # Admin imports the project
    from tests.test_import import (
        WEIRD_DIR,
    )

    prj_id = do_test_import(fastapi, "SCISUM project")
    # Add a sample spanning 2 days
    do_import_a_bit_more_skipping(fastapi, "SCISUM project")
    # Store computation variables
    set_formulae_in_project(fastapi, prj_id, uvp_formulae)
    # Add some data for calculations
    add_concentration_data(fastapi, prj_id)
    # Add a sample with weird data in free columns:
    # rightmost column acq_sub_part in TSV has unusual values
    # date format is mixed
    do_import(fastapi, prj_id, WEIRD_DIR, ADMIN_AUTH)
    # Get the project for update
    url = PROJECT_QUERY_URL.format(project_id=prj_id, manage=True)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    prj_json = rsp.json()
    # Validate everything, otherwise no export.
    obj_ids: List[int] = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    assert len(obj_ids) == 15
    url = OBJECT_SET_CLASSIFY_URL
    obj_ids.sort()
    just_some_objs = obj_ids[::2]  # 1,3,5,...19
    classifications = [-1 for _obj in just_some_objs]  # Keep current
    rsp = fastapi.post(
        url,
        headers=ADMIN_AUTH,
        json={
            "target_ids": just_some_objs,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK

    # Concentrations export by sample
    req_and_filters = {
        "filters": {},
        "request": {"project_id": prj_id, "quantity": "concentration"},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "concentrations_by_sample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Biovolume export by sample
    req_and_filters = {
        "filters": {},
        "request": {"project_id": prj_id, "quantity": "biovolume"},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "biovolumes_by_sample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Biovolume export by subsample AKA Acquisition
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "quantity": "biovolume",
            "summarise_by": "acquisition",
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "biovolumes_by_subsample", only_hdr=True)
    # log = get_log_file(fastapi, job_id)

    # Biovolume export by subsample AKA Acquisition, only validated ones.
    # biovols are identical to un-filtered ones
    req_and_filters = {
        "filters": {"statusfilter": "V"},
        "request": {
            "project_id": prj_id,
            "quantity": "biovolume",
            "summarise_by": "acquisition",
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(fastapi, job_id, "biovolumes_by_subsample_only_v", only_hdr=True)
    # log = get_log_file(fastapi, job_id)


def test_export_summary_list_of_quantities(fastapi):
    """A single request can ask for several quantities at once, e.g.
    abundance + concentration. A single TSV is produced, with one column
    per requested quantity, in the order they were requested."""
    prj_id = do_test_import(fastapi, "SCISUM project list quantities")
    do_import_a_bit_more_skipping(fastapi, "SCISUM project list quantities")
    set_formulae_in_project(fastapi, prj_id, uvp_formulae)
    add_concentration_data(fastapi, prj_id)

    # Validate everything, otherwise empty report
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]  # Keep current
    rsp = fastapi.post(
        url,
        headers=ADMIN_AUTH,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK

    # Ask for abundance AND concentration in a single request
    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "quantity": ["abundance", "concentration"],
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)

    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK

    # A single TSV, not a zip, with both quantities as trailing columns,
    # in request order ("abundance" AKA "count" then "concentration").
    lines = rsp.content.decode("utf-8-sig").splitlines()
    header = lines[0].split("\t")
    assert header[-2:] == ["count", "concentration"]
    # Zero-filled over the (sample, status, taxon) triplets: more than 1 row
    assert len(lines) > 1


def test_export_summary_multi_project(fastapi):
    """When several projects are exported at once (project_id as a comma-separated
    list), results are kept separate per project -- as if several single-project
    exports were concatenated -- and a 'project_id' column is added, in front.
    The 2 projects are imported from the same source data on purpose, so that their
    sample_id/status/taxon triplets collide: project_id must be what disambiguates them."""
    path = str(DATA_DIR / "ref_exports" / "bak_all_images")
    prj_id1 = do_test_import(fastapi, "SCISUM multi project 1", path=path)
    prj_id2 = do_test_import(fastapi, "SCISUM multi project 2", path=path)

    for prj_id in (prj_id1, prj_id2):
        set_formulae_in_project(fastapi, prj_id, uvp_formulae)
        obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
        rsp = fastapi.post(
            OBJECT_SET_CLASSIFY_URL,
            headers=ADMIN_AUTH,
            json={
                "target_ids": obj_ids,
                "classifications": [-1 for _obj in obj_ids],
                "wanted_qualification": "V",
            },
        )
        assert rsp.status_code == status.HTTP_200_OK

    def export_lines(project_id_param):
        req_and_filters = {
            "filters": {},
            "request": {"project_id": project_id_param, "summarise_by": "none"},
        }
        rsp = fastapi.post(
            OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
        )
        assert rsp.status_code == status.HTTP_200_OK
        job_id = get_job_and_wait_until_ok(fastapi, rsp)
        dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
        rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
        assert rsp.status_code == status.HTTP_200_OK
        return rsp.content.decode("utf-8-sig").splitlines()

    single1 = export_lines(str(prj_id1))
    single2 = export_lines(str(prj_id2))
    multi = export_lines("%d,%d" % (prj_id1, prj_id2))

    # Single-project export: no project_id column
    assert single1[0].split("\t")[0] == "status"
    # Multi-project export: project_id is a new, first, column
    header = multi[0].split("\t")
    assert header[0] == "project_id"
    assert header[1:] == single1[0].split("\t")

    # Same rows as the two single-project exports, concatenated: not summed together
    rows_prj1 = [l for l in multi[1:] if l.split("\t", 1)[0] == str(prj_id1)]
    rows_prj2 = [l for l in multi[1:] if l.split("\t", 1)[0] == str(prj_id2)]
    assert [l.split("\t", 1)[1] for l in rows_prj1] == single1[1:]
    assert [l.split("\t", 1)[1] for l in rows_prj2] == single2[1:]
    assert len(rows_prj1) + len(rows_prj2) == len(multi) - 1


def test_export_summary_multi_project_own_formulae(fastapi):
    """Each project keeps its own computation formulae: with several projects in a
    single request, one project's formula must not silently override another's."""
    prj_id1 = do_test_import(fastapi, "SCISUM own formulae 1")
    do_import_a_bit_more_skipping(fastapi, "SCISUM own formulae 1")
    prj_id2 = do_test_import(fastapi, "SCISUM own formulae 2")
    do_import_a_bit_more_skipping(fastapi, "SCISUM own formulae 2")

    for prj_id in (prj_id1, prj_id2):
        add_concentration_data(fastapi, prj_id)
        obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
        rsp = fastapi.post(
            OBJECT_SET_CLASSIFY_URL,
            headers=ADMIN_AUTH,
            json={
                "target_ids": obj_ids,
                "classifications": [-1 for _obj in obj_ids],
                "wanted_qualification": "V",
            },
        )
        assert rsp.status_code == status.HTTP_200_OK

    # Project 1 uses the standard formulae (subsample_coef = 1/sub_part).
    set_formulae_in_project(fastapi, prj_id1, uvp_formulae)
    # Project 2 uses a *different* subsample_coef (doubled), on purpose: if formulae
    # were merged/shared across projects, project 2's concentration would silently
    # come out identical to project 1's instead of being exactly half of it.
    prj2_formulae = dict(uvp_formulae)
    prj2_formulae["subsample_coef"] = "2/ssm.sub_part"
    set_formulae_in_project(fastapi, prj_id2, prj2_formulae)

    def export_lines(project_id_param):
        req_and_filters = {
            "filters": {},
            "request": {
                "project_id": project_id_param,
                "quantity": "concentration",
                "summarise_by": "none",
            },
        }
        rsp = fastapi.post(
            OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
        )
        assert rsp.status_code == status.HTTP_200_OK
        job_id = get_job_and_wait_until_ok(fastapi, rsp)
        dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
        rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
        assert rsp.status_code == status.HTTP_200_OK
        return rsp.content.decode("utf-8-sig").splitlines()

    single1 = export_lines(str(prj_id1))
    single2 = export_lines(str(prj_id2))
    multi = export_lines("%d,%d" % (prj_id1, prj_id2))

    assert len(single1) > 1 and len(single2) > 1

    # The two projects, having different formulae, must produce different values
    concentrations1 = [float(l.split("\t")[-1]) for l in single1[1:]]
    concentrations2 = [float(l.split("\t")[-1]) for l in single2[1:]]
    assert any(c > 0 for c in concentrations1)
    # concentration = 1/subsample_coef/total_water_volume, and project 2's coef is
    # double project 1's -> its concentration is exactly half.
    assert concentrations2 == [c / 2 for c in concentrations1]

    # Multi-project export: each project's rows must match its own single-project
    # export exactly (i.e. use its own formula), not the other project's.
    rows_prj1 = [l for l in multi[1:] if l.split("\t", 1)[0] == str(prj_id1)]
    rows_prj2 = [l for l in multi[1:] if l.split("\t", 1)[0] == str(prj_id2)]
    assert [l.split("\t", 1)[1] for l in rows_prj1] == single1[1:]
    assert [l.split("\t", 1)[1] for l in rows_prj2] == single2[1:]


def test_export_abundances_without_formulae(fastapi):
    """Abundance ('count') never needs any formula: an export must succeed even
    for a project which never had any formula configured."""
    prj_id = do_test_import(fastapi, "SCISUM no formulae")
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    rsp = fastapi.post(
        OBJECT_SET_CLASSIFY_URL,
        headers=ADMIN_AUTH,
        json={
            "target_ids": obj_ids,
            "classifications": [-1 for _obj in obj_ids],
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK

    req_and_filters = {
        "filters": {},
        "request": {"project_id": prj_id, "quantity": "abundance"},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    lines = rsp.content.decode("utf-8-sig").splitlines()
    assert lines[0].split("\t")[-1] == "count"
    assert len(lines) > 1


def test_export_summary_incomplete_formulae(fastapi):
    """Concentration/biovolume must fail fast, with a clear message, when a
    project's formulae don't cover what the requested quantity needs."""
    prj_id = do_test_import(fastapi, "SCISUM incomplete formulae")
    do_import_a_bit_more_skipping(fastapi, "SCISUM incomplete formulae")
    add_concentration_data(fastapi, prj_id)
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    rsp = fastapi.post(
        OBJECT_SET_CLASSIFY_URL,
        headers=ADMIN_AUTH,
        json={
            "target_ids": obj_ids,
            "classifications": [-1 for _obj in obj_ids],
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK

    # Only 'total_water_volume' is configured: 'subsample_coef' is missing for
    # concentration, and 'individual_volume' is missing for biovolume as well.
    set_formulae_in_project(
        fastapi, prj_id, {"total_water_volume": uvp_formulae["total_water_volume"]}
    )

    req_and_filters = {
        "filters": {},
        "request": {
            "project_id": prj_id,
            "quantity": ["abundance", "concentration", "biovolume"],
        },
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK
    job_id = rsp.json()["job_id"]
    job = api_wait_for_stable_job(fastapi, job_id)
    errors = check_job_errors(job)
    combined = "\n".join(errors)
    assert "Incomplete formulae" in combined
    assert "subsample_coef" in combined
    assert "individual_volume" in combined
    assert "concentration" in combined
    assert "biovolume" in combined


def test_export_abundances_filtered_by_taxo(fastapi):
    """Simulate calls to export with an active filter"""

    # TODO: Dup code for the data load
    # Admin imports the project, which is an export expected result

    path = str(DATA_DIR / "ref_exports" / "bak_all_images")
    prj_id = do_test_import(fastapi, "TSV sci export filtered by taxo", path=path)
    set_formulae_in_project(fastapi, prj_id, uvp_formulae)  # Not needed

    # Validate all, otherwise empty report
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]  # Keep current
    rsp = fastapi.post(
        url,
        headers=ADMIN_AUTH,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK

    # Abundance export, per sample with a filter on a category
    req_and_filters = {
        "filters": {
            "taxo": "45072",
            "taxochild": "Y",
        },  # TODO: Not very useful as the test has a very reduced tree
        "request": {"project_id": prj_id},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(
        fastapi, job_id, "abundances_by_sample_filtered_on_cat", only_hdr=True
    )


def test_export_abundances_filtered_by_sample(fastapi):
    """Simulate calls to export with an active filter"""

    # TODO: Dup code for the data load
    # Admin imports the project, which is an export expected result
    path = str(DATA_DIR / "ref_exports" / "bak_all_images")
    prj_id = do_test_import(fastapi, "TSV sci export filtered by sample", path=path)
    set_formulae_in_project(fastapi, prj_id, uvp_formulae)

    # Validate all, otherwise empty report
    obj_ids = _prj_query(fastapi, CREATOR_AUTH, prj_id)
    url = OBJECT_SET_CLASSIFY_URL
    classifications = [-1 for _obj in obj_ids]  # Keep current
    rsp = fastapi.post(
        url,
        headers=ADMIN_AUTH,
        json={
            "target_ids": obj_ids,
            "classifications": classifications,
            "wanted_qualification": "V",
        },
    )
    assert rsp.status_code == status.HTTP_200_OK

    # Abundance export, per sample with a filter on samples
    url = PROJECT_SEARCH_SAMPLES_URL.format(project_id=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    # TODO: This need for IDs in the API is a bit of pain
    sample_ids = [str(r["sampleid"]) for r in rsp.json() if "n2" not in r["orig_id"]]

    req_and_filters = {
        "filters": {"samples": ",".join(sample_ids)},
        "request": {"project_id": prj_id},
    }
    rsp = fastapi.post(
        OBJECT_SET_SUMMARY_EXPORT_URL, headers=ADMIN_AUTH, json=req_and_filters
    )
    assert rsp.status_code == status.HTTP_200_OK

    job_id = get_job_and_wait_until_ok(fastapi, rsp)
    download_and_check(
        fastapi, job_id, "abundances_by_sample_filtered_on_sample", only_hdr=True
    )
