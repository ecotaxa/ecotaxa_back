import logging

from API_operations.ObjectManager import ObjectManager
from starlette import status

from tests.credentials import ADMIN_AUTH, ADMIN_USER_ID
from tests.test_import import do_test_import, do_import_a_bit_more_skipping

# noinspection PyPackageRequirements
from tests.test_update import OBJECT_SET_UPDATE_URL

PROJECT_CLASSIF_STATS_URL = "/project_set/taxo_stats?ids={prj_ids}"

PROJECT_FREE_COLS_STATS_URL = "/projects/{project_id}/stats"

PROJECT_RECOMPUTE = "/projects/{project_id}/recompute_sunpos"


def test_project_stats(fastapi):

    # Admin imports the project

    prj_id = do_test_import(fastapi, "Stats test project")
    # Add a sample spanning 2 days
    do_import_a_bit_more_skipping(fastapi, "Stats test project")
    # Taxa & classif statistics
    url = PROJECT_CLASSIF_STATS_URL.format(prj_ids=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    assert rsp.json() == [
        {
            "nb_dubious": 0,
            "nb_predicted": 11,
            "nb_unclassified": 0,
            "nb_validated": 0,
            "projid": prj_id,
            "used_taxa": [45072, 78418, 84963, 85011, 85012, 85078, 92731],
        }
    ]

    # Get free column statistics
    url = PROJECT_FREE_COLS_STATS_URL.format(project_id=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    expected = [
        "Stats test project",
        "OrderedDict([('by', 'n01'), ('width', 'n02'), ('height', 'n03'), ('area', "
        "'n04'), ('mean', 'n05'), ('major', 'n06'), ('minor', 'n07'), ('feret', "
        "'n08'), ('area_exc', 'n09'), ('thickr', 'n10'), ('esd', 'n11'), "
        "('elongation', 'n12'), ('range', 'n13'), ('meanpos', 'n14'), ('centroids', "
        "'n15'), ('cv', 'n16'), ('sr', 'n17'), ('perimareaexc', 'n18'), "
        "('feretareaexc', 'n19'), ('perimferet', 'n20'), ('perimmajor', 'n21'), "
        "('circex', 'n22'), ('cdexc', 'n23'), ('kurt_mean', 'n24'), ('skew_mean', "
        "'n25'), ('convperim_perim', 'n26'), ('convarea_area', 'n27'), "
        "('symetrieh_area', 'n28'), ('symetriev_area', 'n29'), ('nb1_area', 'n30'), "
        "('nb2_area', 'n31'), ('nb3_area', 'n32'), ('nb1_range', 'n33'), "
        "('nb2_range', 'n34'), ('nb3_range', 'n35'), ('median_mean', 'n36'), "
        "('median_mean_range', 'n37'), ('skeleton_area', 'n38'), ('extra', 't01')])",
        " (0): ",
        "Total: 0 values, dup 0 values",
        "generic_m106_mn01_n1_sml (5): "
        "[9811,10823,#5,u1],[33,65,#5,u1],[47,94,#5,u1],[516,1583,#5,u1],[192.2400054932,241.0399932861,#5,u1],[48.7999992371,70.1999969482,#5,u1],[13.1000003815,41.2000007629,#5,u1],[51.5999984741,102.5999984741,#5,u1],[0,100,#4,u2],[2,2.8239998817,#4,u2],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1],[NaN,NaN,#5,u1]",
        "Total: 190 values, dup 40 values",
        "generic_m106_mn01_n2_sml (3): "
        "[14,10961,#3,u1],[23,56,#3,u1],[26,38,#3,u1],[413,929,#3,u1],[175.5299987793,222.75,#3,u1],[24.7000007629,44.2000007629,#3,u1],[21.2999992371,26.7999992371,#3,u1],[27.2999992371,58.2000007629,#3,u1],[0,9,#2,u2],[1.8600000143,2,#2,u2],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1]",
        "Total: 114 values, dup 40 values",
        "generic_m106_mn01_n3_sml (3): "
        "[14,10961,#3,u1],[23,56,#3,u1],[26,38,#3,u1],[413,929,#3,u1],[175.5299987793,222.75,#3,u1],[24.7000007629,44.2000007629,#3,u1],[21.2999992371,26.7999992371,#3,u1],[27.2999992371,58.2000007629,#3,u1],[0,9,#2,u2],[1.8600000143,2,#2,u2],[1.86,1.86,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1],[NaN,NaN,#3,u1]",
        "Total: 114 values, dup 40 values",
    ]
    actual = rsp.json()
    assert actual == expected


def test_project_redo_sunpos(fastapi):

    # Admin imports the project
    prj_id = do_test_import(fastapi, "Sunpos test project")
    # Add a sample spanning 2 days
    do_import_a_bit_more_skipping(fastapi, "Sunpos test project")
    # Recompure sunpos, should return 0 as all was freshly loaded
    url = PROJECT_RECOMPUTE.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    assert rsp.json() == 0
    # Update first 4 objects
    # TODO: Use the API for querying
    with ObjectManager() as sce:
        objs, _details, _total = sce.query(ADMIN_USER_ID, prj_id, {})
    objs = [an_obj[0] for an_obj in objs]
    assert len(objs) == 11
    url = OBJECT_SET_UPDATE_URL.format(project_id=prj_id)
    req = {"target_ids": objs[0:4], "updates": [{"ucol": "sunpos", "uval": "0"}]}
    rsp = fastapi.post(url, headers=ADMIN_AUTH, json=req)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == 4
    # Recompute sunpos, should restore the right value
    url = PROJECT_RECOMPUTE.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    assert rsp.json() == 4
    # Another time should return 0
    url = PROJECT_RECOMPUTE.format(project_id=prj_id)
    rsp = fastapi.post(url, headers=ADMIN_AUTH)
    assert rsp.status_code == 200
    assert rsp.json() == 0
