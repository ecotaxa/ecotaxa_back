import os
import re
from unittest.mock import MagicMock

import pytest

from API_operations.Status import StatusService, _format_bytes
from DB.User import Role
from helpers.AppConfig import Config


@pytest.fixture(autouse=True)
def reset_config_singleton():
    Config.reset()
    yield
    Config.reset()


def _make_service(mocker, config_ini_path):
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_ini_path)})
    Config.reset()
    sce = StatusService.__new__(StatusService)
    sce.config = Config()
    sce.ro_session = MagicMock()
    return sce


def test_status_unauthenticated(tmp_path, mocker):
    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text("[conf]\n")
    sce = _make_service(mocker, cfg_file)
    assert sce.run(None) == "UP!"


def test_status_unknown_user(tmp_path, mocker):
    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text("[conf]\n")
    sce = _make_service(mocker, cfg_file)
    mocker.patch("API_operations.Status.RightsBO.get_optional_user", return_value=None)
    assert sce.run(999) == "Who?"


def test_status_non_admin_user(tmp_path, mocker):
    existing_dir = tmp_path / "load"
    existing_dir.mkdir()
    missing_dir = tmp_path / "missing_export"

    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text(
        "[conf]\n"
        "APPMANAGER_NAME = Alice\n"
        "APPMANAGER_EMAIL = alice@example.org\n"
        "SECRET_KEY = supersecret\n"
        f"SERVERLOADAREA = {existing_dir}\n"
        f"FTPEXPORTAREA = {missing_dir}\n"
    )
    sce = _make_service(mocker, cfg_file)
    user = MagicMock()
    user.has_role.return_value = False
    mocker.patch("API_operations.Status.RightsBO.get_optional_user", return_value=user)

    out = sce.run(2)
    assert "APPMANAGER_NAME: Alice" in out
    assert "APPMANAGER_EMAIL: alice@example.org" in out
    assert "SECRET_KEY" not in out
    assert "supersecret" not in out
    assert "/somepath (from SERVERLOADAREA): OK" in out
    assert "/somepath (from FTPEXPORTAREA): *** KO ***" in out
    assert "MODELSAREA not found" in out
    assert "USERSFILESAREA not found" in out
    assert "VAULT_DIR not found" in out
    assert "JOBS_DIR not found" in out


def test_status_admin_user_and_env_override(tmp_path, mocker):
    ini_dir = tmp_path / "ini_load"
    ini_dir.mkdir()
    env_dir = tmp_path / "env_models"
    env_dir.mkdir()

    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text(
        "[conf]\n"
        "APPMANAGER_NAME = Alice\n"
        "APPMANAGER_EMAIL = alice@example.org\n"
        "DB_HOST = localhost\n"
        "DB_DATABASE = ecotaxa\n"
        "DB_USER = postgres\n"
        "DB_PASSWORD = mypwd\n"
        "SECRET_KEY = supersecret\n"
        "SECURITY_PASSWORD_SALT = mysalt\n"
        f"SERVERLOADAREA = {ini_dir}\n"
    )
    mocker.patch.dict(os.environ, {"MODELSAREA": str(env_dir)})
    sce = _make_service(mocker, cfg_file)
    admin = MagicMock()
    admin.has_role.return_value = True
    mocker.patch("API_operations.Status.RightsBO.get_optional_user", return_value=admin)

    out = sce.run(1)
    assert "APPMANAGER_NAME: Alice" in out
    assert "SECRET_KEY: *************" in out
    assert "SECURITY_PASSWORD_SALT: *************" in out
    assert "DB_PASSWORD: *************" in out
    assert f"MODELSAREA: {env_dir}" in out
    assert f"{ini_dir} (from SERVERLOADAREA): OK (" in out
    assert f"{env_dir} (from MODELSAREA): OK (" in out
    assert re.search(r"OK \(\d+(?:\.\d+)? ?[BKMGTP] left\)", out)
    assert "FTPEXPORTAREA not found" in out
    assert "USERSFILESAREA not found" in out
    assert "VAULT_DIR not found" in out
    assert "JOBS_DIR not found" in out
    admin.has_role.assert_called_once_with(Role.APP_ADMINISTRATOR)


def test_status_directory_permissions_ko(tmp_path, mocker):
    load_dir = tmp_path / "load"
    load_dir.mkdir()
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text(
        "[conf]\n"
        f"SERVERLOADAREA = {load_dir}\n"
        f"FTPEXPORTAREA = {export_dir}\n"
    )
    sce = _make_service(mocker, cfg_file)
    admin = MagicMock()
    admin.has_role.return_value = True
    mocker.patch("API_operations.Status.RightsBO.get_optional_user", return_value=admin)

    def fake_access(path, mode):
        if str(path) == str(load_dir) and mode == os.W_OK:
            return False
        if str(path) == str(export_dir) and mode == os.R_OK:
            return False
        return True

    mocker.patch("os.access", side_effect=fake_access)

    out = sce.run(1)
    assert f"{load_dir} (from SERVERLOADAREA): *** KO ***" in out
    assert f"{export_dir} (from FTPEXPORTAREA): *** KO ***" in out


@pytest.mark.parametrize(
    "num_bytes,expected",
    [
        (0, "0B"),
        (512, "512B"),
        (1024, "1.0K"),
        (1536, "1.5K"),
        (5 * 1024**2, "5.0M"),
        (12 * 1024**3, "12.0G"),
        (2 * 1024**4, "2.0T"),
        (3 * 1024**5, "3.0P"),
    ],
)
def test_format_bytes(num_bytes, expected):
    assert _format_bytes(num_bytes) == expected


def test_status_free_space_formatting(tmp_path, mocker):
    load_dir = tmp_path / "load"
    load_dir.mkdir()
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text(
        "[conf]\n"
        f"SERVERLOADAREA = {load_dir}\n"
        f"FTPEXPORTAREA = {export_dir}\n"
        f"MODELSAREA = {models_dir}\n"
    )
    sce = _make_service(mocker, cfg_file)
    admin = MagicMock()
    admin.has_role.return_value = True
    mocker.patch("API_operations.Status.RightsBO.get_optional_user", return_value=admin)
    free_space_by_dir = {
        load_dir: 1536,
        export_dir: 5 * 1024**2,
        models_dir: 10 * 1024**3,
    }
    mocker.patch(
        "API_operations.Status.validate_directory",
        side_effect=lambda path, **_kwargs: free_space_by_dir[path],
    )

    out = sce.run(1)
    assert f"{load_dir} (from SERVERLOADAREA): OK (1.5K left)" in out
    assert f"{export_dir} (from FTPEXPORTAREA): OK (5.0M left)" in out
    assert f"{models_dir} (from MODELSAREA): OK (10.0G left)" in out


def test_status_vault_and_jobs_dirs_rw(tmp_path, mocker):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    cfg_file = tmp_path / "config.ini"
    cfg_file.write_text(
        "[conf]\n"
        f"VAULT_DIR = {vault_dir}\n"
        f"JOBS_DIR = {jobs_dir}\n"
    )
    sce = _make_service(mocker, cfg_file)
    admin = MagicMock()
    admin.has_role.return_value = True
    mocker.patch("API_operations.Status.RightsBO.get_optional_user", return_value=admin)

    out = sce.run(1)
    assert f"{vault_dir} (from VAULT_DIR): OK (" in out
    assert f"{jobs_dir} (from JOBS_DIR): OK (" in out

    def no_write_vault_no_read_jobs(path, mode):
        if str(path) == str(vault_dir) and mode == os.W_OK:
            return False
        if str(path) == str(jobs_dir) and mode == os.R_OK:
            return False
        return True

    mocker.patch("os.access", side_effect=no_write_vault_no_read_jobs)
    out = sce.run(1)
    assert f"{vault_dir} (from VAULT_DIR): *** KO ***" in out
    assert f"{jobs_dir} (from JOBS_DIR): *** KO ***" in out
