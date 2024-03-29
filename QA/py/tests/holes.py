#
# Audit output
#
import logging
from pathlib import Path

from API_models.filters import ProjectFiltersDict
from starlette import status

from tests.credentials import USER_AUTH, CREATOR_AUTH
from tests.test_classification import OBJECT_SET_SUMMARY_URL
from tests.test_import import PLAIN_FILE_PATH
from tests.test_import_simple import UPLOAD_FILE_URL

MYFILES_URL = "/my_files/{sub_path}"
COMMON_FILES_URL = "/common_files/?path={sub_path}"


def _get_object_set_stats(fastapi, prj_id, extra, exp_status, exp_text):
    stats_url = OBJECT_SET_SUMMARY_URL.format(project_id=prj_id)
    filters = ProjectFiltersDict()
    filters["statusfilter"] = extra
    filters[
        "taxo?"
    ] = "valid?"  # Hum hum TODO, it seems that pydantic is happy with that, at least in UT
    stats_rsp = fastapi.post(stats_url, headers=USER_AUTH, json=filters)
    assert stats_rsp.status_code == exp_status
    assert str(stats_rsp.text) == exp_text


def test_status(database, fastapi, caplog):
    caplog.set_level(logging.ERROR)
    from tests.test_import import test_import

    prj_id = test_import(database, caplog, "Hole 003")
    _get_object_set_stats(
        fastapi,
        prj_id,
        "",
        status.HTTP_200_OK,
        '{"total_objects":8,"validated_objects":0,"dubious_objects":0,"predicted_objects":8}',
    )
    _get_object_set_stats(
        fastapi,
        prj_id,
        "AND",
        status.HTTP_200_OK,
        '{"total_objects":0,"validated_objects":0,"dubious_objects":0,"predicted_objects":0}',
    )
    # _get_object_set_stats(fastapi, prj_id, "'; select 1,2,3,4 -- -", status.HTTP_200_OK,
    #                       '{"total_objects":1,"validated_objects":2,"dubious_objects":3,"predicted_objects":4}')


def put_path(fastapi, path1="file", path2=None, tag=None, should_fail=False):
    """
    path1: The path accompanying the file in the multipart form
    path2, tag: The params to post, declared in openapi
    """
    with open(PLAIN_FILE_PATH, "rb") as fin:
        files_params = {"file": (path1, fin)}
        params = {"path": path2, "tag": tag}
        upload_rsp = fastapi.post(
            UPLOAD_FILE_URL, headers=CREATOR_AUTH, data=params, files=files_params
        )
        if upload_rsp.status_code == 200:
            assert not should_fail
            srv_file_path = upload_rsp.json()
            assert Path(srv_file_path).resolve().as_posix().startswith("/tmp")
        else:
            assert should_fail


def test_path(fastapi):
    put_path(fastapi)
    put_path(fastapi, "import_test.zip", "subdir/import_test.zip")
    put_path(fastapi, "../../home/laurent/import_test.zip", should_fail=True)
    put_path(
        fastapi,
        "import_test.zip",
        "../../home/laurent/import_test.zip",
        should_fail=True,
    )
    put_path(fastapi, "any", None, "..", should_fail=True)


def get_userdir_path(fastapi, path: str, should_fail=False):
    files_url = MYFILES_URL.format(sub_path=path)
    list_rsp = fastapi.get(files_url, headers=CREATOR_AUTH)
    if list_rsp.status_code == 200:
        assert not should_fail
        dir_content = list_rsp.json()
        assert dir_content["path"] == path.lstrip("/")
        assert len(dir_content["entries"]) == 0
    else:
        assert should_fail


def testGetMyFiles(fastapi):
    get_userdir_path(fastapi, "", False)
    get_userdir_path(fastapi, "/", False)
    get_userdir_path(fastapi, "mydir/../../tmp", True)


def get_commondir_path(fastapi, path: str, should_fail=False):
    # Common files is ../../data
    files_url = COMMON_FILES_URL.format(sub_path=path)
    list_rsp = fastapi.get(files_url, headers=CREATOR_AUTH)
    if list_rsp.status_code == 200:
        assert not should_fail
        dir_content = list_rsp.json()
        assert dir_content["path"] == path.lstrip("/")
        dirs_in_common = set([a_dir["name"] for a_dir in dir_content["entries"]])
        assert "tmp" not in dirs_in_common
        assert "import_test" in dirs_in_common
    else:
        assert should_fail


def testGetCommonFiles(fastapi):
    get_commondir_path(fastapi, "", False)
    get_commondir_path(fastapi, "/", False)
    get_commondir_path(fastapi, "mydir/../../tmp", True)
