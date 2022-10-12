#
# Audit output
#
import logging

from API_models.filters import ProjectFiltersDict
from starlette import status

from tests.credentials import USER_AUTH
from tests.test_classification import OBJECT_SET_SUMMARY_URL


def _get_object_set_stats(fastapi, prj_id, extra, exp_status, exp_text):
    stats_url = OBJECT_SET_SUMMARY_URL.format(project_id=prj_id)
    filters = ProjectFiltersDict()
    filters["statusfilter"] = extra
    filters["taxo?"] = "valid?"  # Hum hum TODO, it seems that pydantic is happy with that, at least in UT
    stats_rsp = fastapi.post(stats_url, headers=USER_AUTH, json=filters)
    assert stats_rsp.status_code == exp_status
    assert str(stats_rsp.text) == exp_text


def test_status(config, database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import
    prj_id = test_import(config, database, caplog, "Hole")
    _get_object_set_stats(fastapi, prj_id, "", status.HTTP_200_OK,
                          '{"total_objects":8,"validated_objects":0,"dubious_objects":0,"predicted_objects":8}')
    _get_object_set_stats(fastapi, prj_id, "AND", status.HTTP_200_OK,
                          '{"total_objects":0,"validated_objects":0,"dubious_objects":0,"predicted_objects":0}')
    # _get_object_set_stats(fastapi, prj_id, "'; select 1,2,3,4 -- -", status.HTTP_200_OK,
    #                       '{"total_objects":1,"validated_objects":2,"dubious_objects":3,"predicted_objects":4}')
