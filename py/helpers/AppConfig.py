# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Application configuration, in a file, pointed at with an env. variable
#

import configparser
import os
import re
import socket
from enum import StrEnum
from pathlib import Path
from typing import (
    Optional,
    Tuple,
    overload,
    Literal,
    List,
)

# Env. variable
ENV_KEY = "APP_CONFIG"


class ConfigKey(StrEnum):
    """
    Standard configuration keys.
    """

    # DB connectivity
    DB_USER = "DB_USER"
    DB_PASSWORD = "DB_PASSWORD"
    DB_HOST = "DB_HOST"
    DB_PORT = "DB_PORT"
    DB_DATABASE = "DB_DATABASE"
    RO_DB_USER = "RO_DB_USER"
    RO_DB_PASSWORD = "RO_DB_PASSWORD"
    RO_DB_HOST = "RO_DB_HOST"
    RO_DB_PORT = "RO_DB_PORT"
    RO_DB_DATABASE = "RO_DB_DATABASE"
    # Application manager & General
    APPMANAGER_EMAIL = "APPMANAGER_EMAIL"
    APPMANAGER_NAME = "APPMANAGER_NAME"
    INSTANCE_ID = "INSTANCE_ID"
    ALL_IN_ONE = "ALL_IN_ONE"
    THUMBSIZELIMIT = "THUMBSIZELIMIT"
    # File & Directory paths
    VAULT_DIR = "VAULT_DIR"
    JOBS_DIR = "JOBS_DIR"
    SERVERLOADAREA = "SERVERLOADAREA"
    FTPEXPORTAREA = "FTPEXPORTAREA"
    MODELSAREA = "MODELSAREA"
    USERSFILESAREA = "USERSFILESAREA"
    DIR_MAIL_TEMPLATES = "DIR_MAIL_TEMPLATES"
    TIMETOLIVE = "TIMETOLIVE"
    MAX_UPLOAD_SIZE = "MAX_UPLOAD_SIZE"
    # Security & Authentication
    SECRET_KEY = "SECRET_KEY"
    SECURITY_PASSWORD_HASH = "SECURITY_PASSWORD_HASH"
    SECURITY_PASSWORD_SALT = "SECURITY_PASSWORD_SALT"
    PASSWORD_SINGLE_HASH = "PASSWORD_SINGLE_HASH"
    ACCESS_TOKEN_TTL = "ACCESS_TOKEN_TTL"
    REFRESH_TOKEN_TTL = "REFRESH_TOKEN_TTL"
    MAX_REFRESH_FAMILIES = "MAX_REFRESH_FAMILIES"
    LEGACY_TOKENS = "LEGACY_TOKENS"
    # Verification, Captcha, URLs
    RECAPTCHAID = "RECAPTCHAID"
    RECAPTCHASECRET = "RECAPTCHASECRET"
    MAX_CAPTCHA_TOKEN_LENGTH = "MAX_CAPTCHA_TOKEN_LENGTH"
    USER_EMAIL_VERIFICATION = "USER_EMAIL_VERIFICATION"
    ACCOUNT_VALIDATION = "ACCOUNT_VALIDATION"
    ADD_TICKET = "ADD_TICKET"
    SERVERURL = "SERVERURL"
    # Mail service
    MAILSERVICE_SECRET_KEY = "MAILSERVICE_SECRET_KEY"
    MAILSERVICE_SALT = "MAILSERVICE_SALT"
    SENDER_ACCOUNT = "SENDER_ACCOUNT"
    # Taxonomy server
    TAXOSERVER_URL = "TAXOSERVER_URL"
    TAXOSERVER_INSTANCE_ID = "TAXOSERVER_INSTANCE_ID"
    TAXOSERVER_SHARED_SECRET = "TAXOSERVER_SHARED_SECRET"
    # OpenID Connect
    OPENID_CLIENT_ID = "OPENID_CLIENT_ID"
    OPENID_CLIENT_SECRET = "OPENID_CLIENT_SECRET"
    OPENID_METADATA_URL = "OPENID_METADATA_URL"
    OPENID_REQUIRE_VERIFIED_EMAIL = "OPENID_REQUIRE_VERIFIED_EMAIL"
    # Mime types & Archives
    ACCEPTED_MIME_TYPES = "ACCEPTED_MIME_TYPES"
    ARCHIVE_EXTENSIONS = "ARCHIVE_EXTENSIONS"
    # CORS
    CORS_ALLOWED_ORIGINS = "CORS_ALLOWED_ORIGINS"
    CORS_ALLOWED_ORIGIN_REGEX = "CORS_ALLOWED_ORIGIN_REGEX"
    # Disk space / Unpack
    UNPACK_MIN_FREE_DISK = "UNPACK_MIN_FREE_DISK"
    MAX_UNPACK_ENTRIES = "MAX_UNPACK_ENTRIES"
    MAX_UNPACKED_SIZE = "MAX_UNPACKED_SIZE"
    MAX_UNPACK_DEPTH = "MAX_UNPACK_DEPTH"
    # Server & Logging
    APP_PORT = "APP_PORT"
    NO_TIME_LOG = "NO_TIME_LOG"


class Config(object):
    """
    The application configuration
    """

    _instance: Optional["Config"] = None

    KNOWN_CONFIG_KEYS = list(ConfigKey)

    def __new__(cls, *args, **kwargs) -> "Config":
        if cls._instance is None:
            instance = super(Config, cls).__new__(cls)
            instance._init_config()
            cls._instance = instance
        return cls._instance

    def _init_config(self) -> None:
        if ENV_KEY in os.environ:
            config_file = Path(os.environ[ENV_KEY])
        else:
            # For dev mode and tests
            config_file = Path("config.ini")
        # Config needs to be in an ini-like format
        config_parser = configparser.ConfigParser()
        if config_file.exists():
            config_parser.read(config_file)
        if "conf" in config_parser:
            self.parser = config_parser["conf"]
        else:
            # Empty config, all from env or defaults
            self.parser = {}  # type: ignore

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing or config reloading)."""
        cls._instance = None

    @overload
    def _get(
        self,
        key: str,
        default: Optional[str] = ...,
        mandatory: Literal[True] = ...,
    ) -> str: ...

    @overload
    def _get(
        self,
        key: str,
        default: Optional[str] = ...,
        mandatory: Literal[False] = ...,
    ) -> Optional[str]: ...

    def _get(
        self,
        key: str,
        default: Optional[str] = None,
        mandatory: bool = False,
    ) -> Optional[str]:
        # Priority to environment variables
        if key in os.environ:
            return os.environ[key]
        val = self.parser.get(key, default)
        if mandatory:
            assert val is not None, f"Mandatory configuration key '{key}' is missing."
        return val

    def vault_dir(self) -> str:
        return self._get(ConfigKey.VAULT_DIR, mandatory=True)

    def jobs_dir(self) -> str:
        return self._get(ConfigKey.JOBS_DIR, mandatory=True)

    def common_folder(self) -> Optional[str]:
        return self._get(ConfigKey.SERVERLOADAREA, mandatory=False)

    def export_folder(self) -> Optional[str]:
        return self._get(ConfigKey.FTPEXPORTAREA, mandatory=False)

    def models_dir(self) -> str:
        return self._get(ConfigKey.MODELSAREA, mandatory=True)

    def secret_key(self) -> str:
        return self._get(ConfigKey.SECRET_KEY, mandatory=True)

    def get_db_address(self, read_only: bool = False) -> Tuple[str, int, str]:
        host = self._get(
            ConfigKey.RO_DB_HOST if read_only else ConfigKey.DB_HOST, mandatory=True
        )
        port_str = self._get(ConfigKey.RO_DB_PORT if read_only else ConfigKey.DB_PORT)
        port = int(port_str) if port_str else 5432
        db_name = self._get(
            ConfigKey.RO_DB_DATABASE if read_only else ConfigKey.DB_DATABASE,
            mandatory=True,
        )
        return host, port, db_name

    def get_db_credentials(self, read_only: bool = False) -> Tuple[str, str]:
        user = self._get(
            ConfigKey.RO_DB_USER if read_only else ConfigKey.DB_USER, mandatory=True
        )
        password = self._get(
            ConfigKey.RO_DB_PASSWORD if read_only else ConfigKey.DB_PASSWORD,
            mandatory=True,
        )
        return user, password

    def get_thumbnails_limit(self) -> int:
        return int(self._get(ConfigKey.THUMBSIZELIMIT, mandatory=True))

    def get_app_manager(self) -> Tuple[str, str]:
        return self._get(ConfigKey.APPMANAGER_NAME, mandatory=True), self._get(
            ConfigKey.APPMANAGER_EMAIL, mandatory=True
        )

    def get_instance_id(self) -> str:
        return self._get(ConfigKey.INSTANCE_ID, "EcoTaxa.01")

    def get_user_email_verification(self) -> Optional[str]:
        return self._get(ConfigKey.USER_EMAIL_VERIFICATION)

    def get_account_validation(self) -> Optional[str]:
        return self._get(ConfigKey.ACCOUNT_VALIDATION)

    def get_recaptchaid(self) -> Optional[str]:
        return self._get(ConfigKey.RECAPTCHAID)

    def get_recaptchasecret(self) -> Optional[str]:
        return self._get(ConfigKey.RECAPTCHASECRET)

    def get_all_in_one(self) -> Optional[str]:
        return self._get(ConfigKey.ALL_IN_ONE)

    def get_dir_mail_templates(self) -> Optional[str]:
        return self._get(ConfigKey.DIR_MAIL_TEMPLATES)

    def get_mailservice_secret_key(self) -> Optional[str]:
        return self._get(ConfigKey.MAILSERVICE_SECRET_KEY)

    def get_mailservice_salt(self) -> Optional[str]:
        return self._get(ConfigKey.MAILSERVICE_SALT)

    def get_sender_account(self) -> Optional[str]:
        # Email settings for account management (CSV: 0: sender email, 1: password (optional for plain SMTP), 2: host, [3: smtp port, 4: imap port, 5: login user])
        return self._get(ConfigKey.SENDER_ACCOUNT)

    def get_add_ticket(self) -> str:
        # string separator - separate  ticket number if ticket software is used and admin comment to user
        return (self._get(ConfigKey.ADD_TICKET) or "").strip()

    def get_account_validation_url(self) -> str:
        # TODO find a way to have multi request url ( list of identified url ???)
        url = self._get(ConfigKey.SERVERURL, mandatory=True).strip()
        return url + ("/" if url[-1] != "/" else "")

    def get_users_files_dir(self) -> str:
        # My files service
        return self._get(ConfigKey.USERSFILESAREA, mandatory=True).strip()

    def get_time_to_live(self) -> str:
        # My files service
        val = self._get(ConfigKey.TIMETOLIVE, mandatory=True)
        return val.strip()

    def get_max_refresh_families(self) -> int:
        return int(self._get(ConfigKey.MAX_REFRESH_FAMILIES, "10"))

    def list_cnf(self) -> List[str]:
        keys: List[str] = list(self.parser.keys())
        for k in self.KNOWN_CONFIG_KEYS:
            if k in os.environ and k not in keys:
                keys.append(k)
        return keys

    def get_max_captcha_token_length(self) -> int:
        return int(self._get(ConfigKey.MAX_CAPTCHA_TOKEN_LENGTH, "4096"))

    def get_max_upload_size(self) -> int:
        return int(self._get(ConfigKey.MAX_UPLOAD_SIZE, "665600"))

    def get_cors_allowed_origins(self) -> List[str]:
        # Exact origins (scheme://host[:port]) of third-party browser apps allowed to read API responses, or '*' for any
        ret = self._get(ConfigKey.CORS_ALLOWED_ORIGINS, "")
        origins = [r.strip() for r in ret.split(",") if r.strip()]
        return origins

    def get_cors_allowed_origin_regex(self) -> Optional[str]:
        # For apps without a fixed origin, e.g. PlanktoScope served by each device
        ret = (self._get(ConfigKey.CORS_ALLOWED_ORIGIN_REGEX) or "").strip()
        return ret or None

    def get_taxoserver_url(self) -> str:
        url = self._get(ConfigKey.TAXOSERVER_URL, mandatory=True).strip()
        return url + ("/" if url[-1] != "/" else "")

    def get_taxoserver_instance_id(self) -> str:
        return self._get(ConfigKey.TAXOSERVER_INSTANCE_ID, mandatory=True)

    def get_taxoserver_shared_secret(self) -> str:
        return self._get(ConfigKey.TAXOSERVER_SHARED_SECRET, mandatory=True)

    def get_security_password_hash(self) -> Optional[str]:
        return self._get(ConfigKey.SECURITY_PASSWORD_HASH)

    def get_security_password_salt(self) -> Optional[str]:
        return self._get(ConfigKey.SECURITY_PASSWORD_SALT)

    def get_access_token_ttl(self) -> int:
        return int(self._get(ConfigKey.ACCESS_TOKEN_TTL, "3600"))

    def get_refresh_token_ttl(self) -> int:
        return int(self._get(ConfigKey.REFRESH_TOKEN_TTL, "864000"))

    def get_legacy_tokens_on(self) -> bool:
        return (self._get(ConfigKey.LEGACY_TOKENS, "on") or "on").strip().lower() in (
            "on",
            "true",
            "1",
            "yes",
        )

    def get_app_port(self) -> int:
        return int(self._get(ConfigKey.APP_PORT, "8000"))

    def get_no_time_log(self) -> bool:
        return (self._get(ConfigKey.NO_TIME_LOG, "off") or "off").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    def get_openid_require_verified_email(self) -> bool:
        """
        Whether an OpenID login is refused when the provider did not mark the
        email as verified. Defaults to on, as an unverified email must not be
        used to attach an external identity to a local account.
        """
        val = self._get(ConfigKey.OPENID_REQUIRE_VERIFIED_EMAIL, "on")
        return (val or "on").strip().lower() in ("on", "true", "1", "yes")

    def get_openid_config(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Return (client_id, client_secret, metadata_url) if all are present,
        or (None, None, None) if none are present.
        Raise an exception if only some are present.
        """
        client_id = self._get(ConfigKey.OPENID_CLIENT_ID)
        client_secret = self._get(ConfigKey.OPENID_CLIENT_SECRET)
        metadata_url = self._get(ConfigKey.OPENID_METADATA_URL)

        configs = [client_id, client_secret, metadata_url]
        if all(configs):
            return client_id, client_secret, metadata_url
        if not any(configs):
            return None, None, None

        missing = []
        if not client_id:
            missing.append(ConfigKey.OPENID_CLIENT_ID)
        if not client_secret:
            missing.append(ConfigKey.OPENID_CLIENT_SECRET)
        if not metadata_url:
            missing.append(ConfigKey.OPENID_METADATA_URL)
        raise ValueError(
            f"Inconsistent OpenID configuration. Missing: {', '.join(missing)}"
        )

    # The unpack limits below are all off (0) when absent from config.ini
    def get_max_unpacked_size(self) -> int:
        """Max total size (bytes) of an upload once unpacked, nested archives included. 0: no limit."""
        return int(self._get(ConfigKey.MAX_UNPACKED_SIZE, "0") or 0)

    def get_max_unpack_depth(self) -> int:
        """Max nesting level of archives in an upload, the uploaded archive being 1. 0: no limit."""
        return int(self._get(ConfigKey.MAX_UNPACK_DEPTH, "0") or 0)

    def get_max_unpack_entries(self) -> int:
        """Max number of entries in an upload once unpacked, nested archives included. 0: no limit."""
        return int(self._get(ConfigKey.MAX_UNPACK_ENTRIES, "0") or 0)

    def get_unpack_min_free_disk(self) -> Tuple[Optional[float], Optional[int]]:
        """
        Free disk space that unpacking must leave, either a percentage of the disk, e.g. "10%",
        returned as (ratio, None), or a number of bytes, returned as (None, bytes).
        0 or 0%: no check of free disk space.
        """
        val = (self._get(ConfigKey.UNPACK_MIN_FREE_DISK, "0") or "0").strip()
        if val.endswith("%"):
            percent = float(val[:-1])
            assert 0 <= percent < 100, f"{ConfigKey.UNPACK_MIN_FREE_DISK} percentage must be in [0, 100["
            return percent / 100, None
        nb_bytes = int(val)
        assert nb_bytes >= 0, "{ConfigKey.UNPACK_MIN_FREE_DISK} must be >= 0"
        return None, nb_bytes

    def validate(self):
        """
        Read all configuration values to ensure they are present and valid.
        """
        vault_dir = self.vault_dir()
        jobs_dir = self.jobs_dir()
        common_folder = self.common_folder()
        export_folder = self.export_folder()
        users_files_dir = self.get_users_files_dir()

        for d in [
            vault_dir,
            jobs_dir,
            common_folder,
            export_folder,
            users_files_dir,
        ]:
            if d is None:
                continue
            path = Path(d)
            assert path.is_dir(), f"Directory '{d}' does not exist."
            if d != common_folder:
                assert os.access(path, os.R_OK), f"Directory '{d}' is not readable."
            if d != export_folder:
                assert os.access(path, os.W_OK), f"Directory '{d}' is not writable."

        db_address = self.get_db_address(read_only=False)
        ro_db_address = self.get_db_address(read_only=True)
        for host in [
            db_address[0],
            ro_db_address[0],
        ]:
            try:
                socket.gethostbyname(host)
            except socket.gaierror:
                assert False, f"DB host '{host}' is not reachable."

        self.get_db_credentials(read_only=False)
        self.get_db_credentials(read_only=True)
        self.get_thumbnails_limit()
        self.secret_key()
        self.get_app_manager()
        self.get_user_email_verification()
        self.get_account_validation()
        self.get_recaptchaid()
        self.get_recaptchasecret()
        self.get_all_in_one()
        self.get_mailservice_secret_key()
        self.get_mailservice_salt()
        self.get_sender_account()
        self.get_add_ticket()
        self.get_account_validation_url()
        self.get_time_to_live()
        self.get_max_captcha_token_length()
        self.get_max_upload_size()
        assert self.get_max_unpacked_size() >= 0, "MAX_UNPACKED_SIZE must be >= 0"
        assert self.get_max_unpack_depth() >= 0, "MAX_UNPACK_DEPTH must be >= 0"
        assert self.get_max_unpack_entries() >= 0, "MAX_UNPACK_ENTRIES must be >= 0"
        self.get_unpack_min_free_disk()
        self.get_taxoserver_url()
        self.get_openid_config()
        self.get_openid_require_verified_email()
        self.get_cors_allowed_origins()
        cors_origin_regex = self.get_cors_allowed_origin_regex()
        if cors_origin_regex is not None:
            try:
                re.compile(cors_origin_regex)
            except re.error as e:
                assert False, f"CORS_ALLOWED_ORIGIN_REGEX is not a valid regex: {e}"
