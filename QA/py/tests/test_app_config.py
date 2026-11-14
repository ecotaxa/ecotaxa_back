import os
from enum import StrEnum

import pytest
from helpers.AppConfig import Config, ConfigKey


# Helper to create a dummy config file
def create_config_file(path, content):
    with open(path, "w") as f:
        f.write("[conf]\n")
        for k, v in content.items():
            f.write(f"{k} = {v}\n")


@pytest.fixture(autouse=True)
def reset_config_singleton():
    Config.reset()
    yield
    Config.reset()


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

    export = tmp_path / "export"
    export.mkdir()

    yield {
        "VAULT_DIR": str(vault),
        "JOBS_DIR": str(jobs),
        "USERSFILESAREA": str(users),
        "SERVERLOADAREA": str(common),
        "FTPEXPORTAREA": str(export),
    }

    # Cleanup


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
        assert cfg._get("SOME_KEY") == "some_value"
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


@pytest.mark.parametrize(
    "config_key, folder_key, access_mode, expected_error",
    [
        ("SERVERLOADAREA", "SERVERLOADAREA", os.W_OK, "is not writable"),
        ("FTPEXPORTAREA", "FTPEXPORTAREA", os.R_OK, "is not readable"),
    ],
)
def test_config_validate_fails_when_folder_permissions_invalid(
    tmp_path,
    temp_dirs,
    base_config,
    mocker,
    config_key,
    folder_key,
    access_mode,
    expected_error,
):
    config_path = tmp_path / "config.ini"
    content = base_config.copy()
    folder_path = temp_dirs[folder_key]
    content.update({config_key: folder_path})

    create_config_file(config_path, content)

    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})
    mocker.patch("socket.gethostbyname", side_effect=lambda x: "127.0.0.1")

    # Workaround: os.chmod is not effective in some CI environments (like GitHub Actions).
    # Mock os.access to simulate permission issues.
    original_access = os.access

    def mocked_access(path, mode):
        if str(path) == str(folder_path) and mode == access_mode:
            return False
        return original_access(path, mode)

    mocker.patch("os.access", side_effect=mocked_access)

    cfg = Config()
    with pytest.raises(AssertionError, match=expected_error):
        cfg.validate()


def test_config_singleton_same_instance(tmp_path, mocker):
    config_path = tmp_path / "config.ini"
    create_config_file(config_path, {"SOME_KEY": "some_value"})
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})

    cfg1 = Config()
    cfg2 = Config()
    assert cfg1 is cfg2
    assert cfg1._get("SOME_KEY") == "some_value"


def test_config_reset_allows_reinit(tmp_path, mocker):
    config_path1 = tmp_path / "config1.ini"
    create_config_file(config_path1, {"KEY": "value1"})
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path1)})

    cfg1 = Config()
    assert cfg1._get("KEY") == "value1"

    config_path2 = tmp_path / "config2.ini"
    create_config_file(config_path2, {"KEY": "value2"})
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path2)})

    Config.reset()
    cfg2 = Config()
    assert cfg2 is not cfg1
    assert cfg2._get("KEY") == "value2"



@pytest.fixture
def no_cors_env(mocker):
    # fastapi_fixture sets them in env for test_cors.py, and env has priority over the file.
    # Via mocker, not monkeypatch: the tests' own mocker.patch.dict(os.environ) must be undone before, not after.
    mocker.patch.dict(os.environ)
    os.environ.pop("CORS_ALLOWED_ORIGINS", None)
    os.environ.pop("CORS_ALLOWED_ORIGIN_REGEX", None)


def test_config_cors(tmp_path, base_config, mocker, mock_socket, no_cors_env):
    config_path = tmp_path / "config.ini"
    content = base_config.copy()
    content.update(
        {
            "CORS_ALLOWED_ORIGINS": " https://a.example.org, ,http://b.example.org:8080 ",
            "CORS_ALLOWED_ORIGIN_REGEX": r"^http://pkscope-[a-z0-9-]*\.local$",
        }
    )
    create_config_file(config_path, content)
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})

    cfg = Config()
    assert cfg.get_cors_allowed_origins() == [
        "https://a.example.org",
        "http://b.example.org:8080",
    ]
    assert cfg.get_cors_allowed_origin_regex() == r"^http://pkscope-[a-z0-9-]*\.local$"
    cfg.validate()


def test_config_cors_any(tmp_path, base_config, mocker, mock_socket, no_cors_env):
    # Same as the former nginx add_header 'Access-Control-Allow-Origin' '*'
    config_path = tmp_path / "config.ini"
    content = base_config.copy()
    content.update({"CORS_ALLOWED_ORIGINS": "*"})
    create_config_file(config_path, content)
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})

    cfg = Config()
    assert cfg.get_cors_allowed_origins() == ["*"]
    cfg.validate()


def test_config_cors_absent(tmp_path, base_config, mocker, no_cors_env):
    config_path = tmp_path / "config.ini"
    create_config_file(config_path, base_config)
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})

    cfg = Config()
    assert cfg.get_cors_allowed_origins() == []
    assert cfg.get_cors_allowed_origin_regex() is None


@pytest.mark.parametrize(
    "key, value, expected_error",
    [
        ("CORS_ALLOWED_ORIGIN_REGEX", "^http://(unclosed", "not a valid regex"),
    ],
)
def test_config_cors_invalid(
    tmp_path, base_config, mocker, mock_socket, no_cors_env, key, value, expected_error
):
    config_path = tmp_path / "config.ini"
    content = base_config.copy()
    content.update({key: value})
    create_config_file(config_path, content)
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(config_path)})

    cfg = Config()
    with pytest.raises(AssertionError, match=expected_error):
        cfg.validate()


def test_config_list_cnf_all_env(tmp_path, mocker):
    non_existent_config = tmp_path / "nonexistent.ini"
    env_vars = {
        "APP_CONFIG": str(non_existent_config),
        "APPMANAGER_EMAIL": "admin@example.com",
        "APPMANAGER_NAME": "Admin Name",
        "VAULT_DIR": "/tmp/vault",
        "SECRET_KEY": "supersecret",
        "CUSTOM_ENV_KEY": "some_value",
    }
    mocker.patch.dict(os.environ, env_vars, clear=False)

    cfg = Config()
    keys = cfg.list_cnf()

    # Known keys in env should be listed
    assert "APPMANAGER_EMAIL" in keys
    assert "APPMANAGER_NAME" in keys
    assert "VAULT_DIR" in keys
    assert "SECRET_KEY" in keys
    # Key not set in env should not be listed
    assert "FTPEXPORTAREA" not in keys
    assert "NONEXISTENT_KEY" not in keys

    # _get and methods should retrieve values using exact key
    assert cfg._get("APPMANAGER_EMAIL") == "admin@example.com"
    assert cfg._get("VAULT_DIR") == "/tmp/vault"
    assert cfg.get_app_manager() == ("Admin Name", "admin@example.com")
    assert cfg.vault_dir() == "/tmp/vault"
    assert cfg.secret_key() == "supersecret"


def test_config_list_cnf_mixed_file_and_env(tmp_path, mocker):
    config_path = tmp_path / "config.ini"
    create_config_file(
        config_path,
        {
            "FILE_ONLY_KEY": "from_file",
            "OVERRIDDEN_KEY": "from_file",
            "VAULT_DIR": "/vault/from/file",
        },
    )
    mocker.patch.dict(
        os.environ,
        {
            "APP_CONFIG": str(config_path),
            "OVERRIDDEN_KEY": "from_env",
            "JOBS_DIR": "/jobs/from/env",
        },
        clear=False,
    )

    cfg = Config()
    keys = cfg.list_cnf()

    assert "file_only_key" in keys
    assert "vault_dir" in keys
    assert "JOBS_DIR" in keys

    assert cfg._get("FILE_ONLY_KEY") == "from_file"
    assert cfg._get("OVERRIDDEN_KEY") == "from_env"
    assert cfg.vault_dir() == "/vault/from/file"
    assert cfg.jobs_dir() == "/jobs/from/env"


def test_config_key_enum_values():
    assert issubclass(ConfigKey, StrEnum)
    assert ConfigKey.DB_USER == "DB_USER"
    assert ConfigKey.VAULT_DIR == "VAULT_DIR"
    assert ConfigKey.SECRET_KEY == "SECRET_KEY"
    assert isinstance(ConfigKey.VAULT_DIR, str)


def test_config_get_with_config_key_enum(tmp_path, mocker):
    non_existent_config = tmp_path / "nonexistent.ini"
    env_vars = {
        "APP_CONFIG": str(non_existent_config),
        "VAULT_DIR": "/custom/vault/path",
        "APPMANAGER_EMAIL": "manager@domain.test",
        "MODELSAREA": "/custom/models/path",
        "TAXOSERVER_INSTANCE_ID": "42",
        "TAXOSERVER_SHARED_SECRET": "mysecret",
        "INSTANCE_ID": "EcoTaxa.Test",
        "MAX_REFRESH_FAMILIES": "15",
        "SECURITY_PASSWORD_HASH": "pbkdf2_sha256",
        "SECURITY_PASSWORD_SALT": "mysalt",
        "ACCESS_TOKEN_TTL": "1800",
        "REFRESH_TOKEN_TTL": "7200",
        "LEGACY_TOKENS": "off",
        "APP_PORT": "9000",
        "NO_TIME_LOG": "1",
    }
    mocker.patch.dict(os.environ, env_vars, clear=False)

    cfg = Config()
    assert cfg._get(ConfigKey.VAULT_DIR) == "/custom/vault/path"
    assert cfg._get(ConfigKey.APPMANAGER_EMAIL) == "manager@domain.test"
    assert ConfigKey.VAULT_DIR in cfg.list_cnf()
    assert ConfigKey.APPMANAGER_EMAIL in cfg.list_cnf()

    assert cfg.models_dir() == "/custom/models/path"
    assert cfg.get_taxoserver_instance_id() == "42"
    assert cfg.get_taxoserver_shared_secret() == "mysecret"
    assert cfg.get_instance_id() == "EcoTaxa.Test"
    assert cfg.get_max_refresh_families() == 15
    assert cfg.get_security_password_hash() == "pbkdf2_sha256"
    assert cfg.get_security_password_salt() == "mysalt"
    assert cfg.get_access_token_ttl() == 1800
    assert cfg.get_refresh_token_ttl() == 7200
    assert cfg.get_legacy_tokens_on() is False
    assert cfg.get_app_port() == 9000
    assert cfg.get_no_time_log() is True


def test_config_app_port_and_no_time_log_defaults(tmp_path, mocker):
    non_existent_config = tmp_path / "nonexistent.ini"
    mocker.patch.dict(os.environ, {"APP_CONFIG": str(non_existent_config)}, clear=True)

    cfg = Config()
    assert cfg.get_app_port() == 8000
    assert cfg.get_no_time_log() is False
