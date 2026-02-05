# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Application configuration, in a file, pointed at with an env. variable
#

import configparser
import os
import socket
from pathlib import Path
from typing import Optional, KeysView, Tuple, overload, Literal

# Env. variable
ENV_KEY = "APP_CONFIG"


class Config(object):
    """
    The application configuration
    """

    def __init__(self):
        if ENV_KEY in os.environ:
            config_file = Path(os.environ[ENV_KEY])
        else:
            # For dev mode and tests
            config_file = "config.ini"
        # Config needs to be in an ini-like format
        config_parser = configparser.ConfigParser()
        config_parser.read(config_file)
        self.parser = config_parser["conf"]

    @overload
    def _get(
        self, key: str, default: Optional[str] = ..., mandatory: Literal[True] = ...
    ) -> str: ...

    @overload
    def _get(
        self, key: str, default: Optional[str] = ..., mandatory: Literal[False] = ...
    ) -> Optional[str]: ...

    def _get(
        self, key: str, default: Optional[str] = None, mandatory: bool = False
    ) -> Optional[str]:
        # Priority to environment variables
        if key in os.environ:
            return os.environ[key]
        val = self.parser.get(key, default)
        if mandatory:
            assert val is not None, f"Mandatory configuration key '{key}' is missing."
        return val

    def vault_dir(self) -> str:
        return self._get("VAULT_DIR", mandatory=True)

    def jobs_dir(self) -> str:
        return self._get("JOBS_DIR", mandatory=True)

    def common_folder(self) -> str:
        return self._get("SERVERLOADAREA", mandatory=True)

    def export_folder(self) -> str:
        return self._get("FTPEXPORTAREA", mandatory=True)

    def secret_key(self) -> str:
        return self._get("SECRET_KEY", mandatory=True)

    def get_db_address(self, read_only: bool = False) -> Tuple[str, int, str]:
        prfx = "RO_" if read_only else ""
        host = self._get(prfx + "DB_HOST", mandatory=True)
        port_str = self._get(prfx + "DB_PORT")
        port = int(port_str) if port_str else 5432
        db_name = self._get(prfx + "DB_DATABASE", mandatory=True)
        return host, port, db_name

    def get_db_credentials(self, read_only: bool = False) -> Tuple[str, str]:
        prfx = "RO_" if read_only else ""
        user = self._get(prfx + "DB_USER", mandatory=True)
        password = self._get(prfx + "DB_PASSWORD", mandatory=True)
        return user, password

    def get_thumbnails_limit(self) -> int:
        return int(self._get("THUMBSIZELIMIT", mandatory=True))

    def get_app_manager(self) -> Tuple[str, str]:
        return self._get("APPMANAGER_NAME", mandatory=True), self._get(
            "APPMANAGER_EMAIL", mandatory=True
        )

    def get_user_email_verification(self) -> Optional[str]:
        return self._get("USER_EMAIL_VERIFICATION")

    def get_account_validation(self) -> Optional[str]:
        return self._get("ACCOUNT_VALIDATION")

    def get_recaptchaid(self) -> Optional[str]:
        return self._get("RECAPTCHAID")

    def get_recaptchasecret(self) -> Optional[str]:
        return self._get("RECAPTCHASECRET")

    def get_all_in_one(self) -> Optional[str]:
        return self._get("ALL_IN_ONE")

    def get_dir_mail_templates(self) -> Optional[str]:
        return self._get("DIR_MAIL_TEMPLATES")

    def get_mailservice_secret_key(self) -> Optional[str]:
        return self._get("MAILSERVICE_SECRET_KEY")

    def get_mailservice_salt(self) -> Optional[str]:
        return self._get("MAILSERVICE_SALT")

    def get_sender_account(self) -> Optional[str]:
        # email address used in account management - 0 email - 1 pwd - 2 - dns - 3 port
        return self._get("SENDER_ACCOUNT")

    def get_add_ticket(self) -> str:
        # string separator - separate  ticket number if ticket software is used and admin comment to user
        return (self._get("ADD_TICKET") or "").strip()

    def get_account_validation_url(self) -> Optional[str]:
        # TODO find a way to have multi request url ( list of identified url ???)
        url = (self._get("SERVERURL") or "").strip()
        if not url:
            return None
        return url + ("/" if url[-1] != "/" else "")

    def get_users_files_dir(self) -> str:
        # My files service
        return self._get("USERSFILESAREA", mandatory=True).strip()

    def get_time_to_live(self) -> str:
        # My files service
        val = self._get("TIMETOLIVE", mandatory=True)
        return val.strip()

    def get_cnf(self, key: str, default: Optional[str] = None) -> Optional[str]:
        # TODO: stop using so we can enumerate the keys
        return self._get(key, default)

    def list_cnf(self) -> KeysView[str]:
        return self.parser.keys()

    def get_max_captcha_token_length(self) -> int:
        return int(self._get("MAX_CAPTCHA_TOKEN_LENGTH", "4096"))

    def get_max_upload_size(self) -> int:
        return int(self._get("MAX_UPLOAD_SIZE", "665600"))

    def get_taxoserver_url(self) -> str:
        url = self._get("TAXOSERVER_URL", mandatory=True).strip()
        return url + ("/" if url[-1] != "/" else "")

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
            path = Path(d)
            assert path.is_dir(), f"Directory '{d}' does not exist."
            assert os.access(path, os.R_OK), f"Directory '{d}' is not readable."
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
        self.get_taxoserver_url()
