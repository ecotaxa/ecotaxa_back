import os

import pytest
from helpers.AppConfig import Config


# Helper to create a dummy config file
def create_config_file(path, content):
    with open(path, "w") as f:
        f.write("[conf]\n")
        for k, v in content.items():
            f.write(f"{k} = {v}\n")


@pytest.fixture
def temp_dirs(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    jobs = tmp_path / "jobs"
    jobs.mkdir()
    users = tmp_path / "users"
    users.mkdir()

    common = tmp_path / "common"
    common.mkdir()
    # Read-only common
    os.chmod(common, 0o555)

    export = tmp_path / "export"
    export.mkdir()
    # Write-only (or at least non-readable) export
    # Note: on some systems, write-only might still allow some access, but we want to test if it's NOT readable
    os.chmod(export, 0o222)

    yield {
        "VAULT_DIR": str(vault),
        "JOBS_DIR": str(jobs),
        "USERSFILESAREA": str(users),
        "SERVERLOADAREA": str(common),
        "FTPEXPORTAREA": str(export),
    }

    # Cleanup: restore permissions to allow deletion
    os.chmod(common, 0o777)
    os.chmod(export, 0o777)


@pytest.fixture
def mock_socket(mocker):
    mocker.patch("socket.gethostbyname", side_effect=lambda x: "127.0.0.1")


@pytest.fixture
def base_config(temp_dirs):
    return {
        "DB_USER": "user",
        "DB_PASSWORD": "pwd",
        "DB_HOST": "localhost",
        "DB_DATABASE": "db",
        "RO_DB_USER": "user",
        "RO_DB_PASSWORD": "pwd",
        "RO_DB_HOST": "localhost",
        "RO_DB_DATABASE": "db",
        "SECRET_KEY": "secret",
        "VAULT_DIR": temp_dirs["VAULT_DIR"],
        "JOBS_DIR": temp_dirs["JOBS_DIR"],
        "USERSFILESAREA": temp_dirs["USERSFILESAREA"],
        "THUMBSIZELIMIT": "400",
        "APPMANAGER_NAME": "name",
        "APPMANAGER_EMAIL": "email",
        "TAXOSERVER_URL": "http://localhost",
        "TIMETOLIVE": "60",
    }


def test_config_missing_file_all_env(
    tmp_path, temp_dirs, base_config, mocker, mock_socket
):
    # Ensure no config file exists at the default location
    config_path = tmp_path / "non_existent_config.ini"
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})

    # Set all mandatory environment variables
    config = base_config.copy()
    config.update(
        {
            "DB_USER": "env_user",
            "DB_PASSWORD": "env_pwd",
            "DB_DATABASE": "env_db",
            "RO_DB_USER": "env_ro_user",
            "RO_DB_PASSWORD": "env_ro_pwd",
            "RO_DB_DATABASE": "env_ro_db",
            "SECRET_KEY": "env_secret",
            "THUMBSIZELIMIT": "500",
            "APPMANAGER_NAME": "env_name",
            "APPMANAGER_EMAIL": "env_email",
            "TAXOSERVER_URL": "http://env-localhost",
            "TIMETOLIVE": "120",
        }
    )
    mocker.patch.dict(os.environ, config)

    cfg = Config()
    # Check if values are correctly picked from environment
    assert cfg.get_db_credentials()[0] == "env_user"
    assert cfg.get_thumbnails_limit() == 500
    assert cfg.vault_dir() == temp_dirs["VAULT_DIR"]

    # Validate should pass
    cfg.validate()


def test_config_env_priority(tmp_path, temp_dirs, base_config, mocker, mock_socket):
    config_path = tmp_path / "config.ini"
    content = base_config.copy()
    content.update(
        {
            "DB_USER": "file_user",
            "DB_PASSWORD": "file_password",
            "DB_DATABASE": "file_db",
            "RO_DB_USER": "file_user",
            "RO_DB_PASSWORD": "file_password",
            "RO_DB_DATABASE": "file_db",
            "SECRET_KEY": "file_secret",
            "THUMBSIZELIMIT": "400",
            "APPMANAGER_NAME": "file_name",
            "APPMANAGER_EMAIL": "file_email",
            "TAXOSERVER_URL": "http://file-localhost",
            "TIMETOLIVE": "60",
        }
    )
    create_config_file(config_path, content)
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})

    # Override one mandatory value via environment
    mocker.patch.dict(os.environ, {"DB_USER": "env_user"})

    cfg = Config()
    # Should pick 'env_user' instead of 'file_user'
    assert cfg.get_db_credentials()[0] == "env_user"
    # Should pick 'file_password' as it's not in env
    assert cfg.get_db_credentials()[1] == "file_password"

    cfg.validate()


def test_config_missing_mandatory_raises(tmp_path, mocker):
    config_path = tmp_path / "config.ini"
    # Create an empty config file
    create_config_file(config_path, {})
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})

    cfg = Config()
    # VAULT_DIR is mandatory and not set
    with pytest.raises(
        AssertionError, match="Mandatory configuration key 'VAULT_DIR' is missing"
    ):
        cfg.vault_dir()


def test_config_empty_file_and_no_env(tmp_path, mocker):
    # This test ensures that even with an empty config and no env vars, the app doesn't crash on init
    config_path = tmp_path / "empty_config.ini"
    create_config_file(config_path, {})
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})

    cfg = Config()
    assert cfg.parser == {}


def test_config_no_env_key_defaults_to_config_ini(tmp_path, mocker):
    # If APP_CONFIG is not in env, it should try to read 'config.ini' from current dir
    mocker.patch.dict(os.environ, {}, clear=False)
    os.environ.pop("APP_CONFIG", None)

    config_file = tmp_path / "config.ini"
    create_config_file(config_file, {"SOME_KEY": "some_value"})

    # This is a bit tricky because Config() uses Path("config.ini")
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        cfg = Config()
        assert cfg.get_cnf("SOME_KEY") == "some_value"
    finally:
        os.chdir(cwd)


def test_config_missing_file_no_env_key_no_default_file(tmp_path, mocker):
    mocker.patch.dict(os.environ, {}, clear=False)
    os.environ.pop("APP_CONFIG", None)
    cwd = os.getcwd()
    os.chdir(tmp_path)  # No config.ini here
    try:
        cfg = Config()
        assert cfg.parser == {}
    finally:
        os.chdir(cwd)


def test_config_validate_optional_folders_missing(tmp_path, base_config, mocker):
    config_path = tmp_path / "config.ini"
    content = base_config.copy()
    # SERVERLOADAREA and FTPEXPORTAREA are missing
    create_config_file(config_path, content)

    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})
    # Mocking socket.gethostbyname to avoid network issues
    mocker.patch("socket.gethostbyname", side_effect=lambda x: "127.0.0.1")

    cfg = Config()
    assert cfg.common_folder() is None
    assert cfg.export_folder() is None
    cfg.validate()  # Should not raise


def test_config_validate_with_folders_permissions(
    tmp_path, temp_dirs, base_config, mocker
):
    config_path = tmp_path / "config.ini"
    content = base_config.copy()
    content.update(
        {
            "SERVERLOADAREA": temp_dirs["SERVERLOADAREA"],
            "FTPEXPORTAREA": temp_dirs["FTPEXPORTAREA"],
        }
    )
    create_config_file(config_path, content)

    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})
    mocker.patch("socket.gethostbyname", side_effect=lambda x: "127.0.0.1")

    cfg = Config()
    assert cfg.common_folder() == temp_dirs["SERVERLOADAREA"]
    assert cfg.export_folder() == temp_dirs["FTPEXPORTAREA"]

    cfg.validate()  # Should not raise


def test_config_validate_fails_when_common_not_readable(
    tmp_path, temp_dirs, base_config, mocker
):
    config_path = tmp_path / "config.ini"
    content = base_config.copy()
    content.update({"SERVERLOADAREA": temp_dirs["SERVERLOADAREA"]})
    # Make common NOT readable
    os.chmod(temp_dirs["SERVERLOADAREA"], 0o000)

    create_config_file(config_path, content)

    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})
    mocker.patch("socket.gethostbyname", side_effect=lambda x: "127.0.0.1")

    cfg = Config()
    with pytest.raises(AssertionError, match="is not readable"):
        cfg.validate()


def test_config_validate_fails_when_export_not_writable(
    tmp_path, temp_dirs, base_config, mocker
):
    config_path = tmp_path / "config.ini"
    content = base_config.copy()
    content.update({"FTPEXPORTAREA": temp_dirs["FTPEXPORTAREA"]})
    # Make export NOT writable
    os.chmod(temp_dirs["FTPEXPORTAREA"], 0o555)

    create_config_file(config_path, content)

    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})
    mocker.patch("socket.gethostbyname", side_effect=lambda x: "127.0.0.1")

    cfg = Config()
    with pytest.raises(AssertionError, match="is not writable"):
        cfg.validate()
