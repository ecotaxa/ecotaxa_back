# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Application configuration, in a file, pointed at with an env. variable
#

import configparser
import os
from pathlib import Path
from typing import Optional, KeysView, Tuple

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

    def vault_dir(self) -> str:
        return self.parser.get("VAULT_DIR")

    def jobs_dir(self) -> str:
        return self.parser.get("JOBS_DIR")

    def common_folder(self) -> str:
        return self.parser.get("SERVERLOADAREA")

    def export_folder(self) -> str:
        return self.parser.get("FTPEXPORTAREA")

    def secret_key(self) -> str:
        return self.parser.get("SECRET_KEY")

    def get_db_address(self, read_only: bool = False) -> Tuple[str, int, str]:
        prfx = "RO_" if read_only else ""
        host = self.parser.get(prfx + "DB_HOST")
        port = self.parser.getint(prfx + "DB_PORT", 5432)
        db_name = self.parser.get(prfx + "DB_DATABASE")
        return host, port, db_name

    def get_db_credentials(self, read_only: bool = False) -> Tuple[str, str]:
        prfx = "RO_" if read_only else ""
        user = self.parser.get(prfx + "DB_USER")
        password = self.parser.get(prfx + "DB_PASSWORD")
        return user, password

    def get_thumbnails_limit(self) -> int:
        return self.parser.getint("THUMBSIZELIMIT")

    def get_app_manager(self) -> Tuple[Optional[str], Optional[str]]:
        return self.parser.get("APPMANAGER_NAME"), self.parser.get("APPMANAGER_EMAIL")

    def get_user_email_verification(self) -> Optional[str]:
        return self.parser.get("USER_EMAIL_VERIFICATION")

    def get_account_validation(self) -> Optional[str]:
        return self.parser.get("ACCOUNT_VALIDATION")

    def get_dir_mail_templates(self) -> Optional[str]:
        return self.parser.get("DIR_MAIL_TEMPLATES")

    def get_recaptchaid(self) -> Optional[str]:
        return self.parser.get("RECAPTCHAID")

    def get_recaptchasecret(self) -> Optional[str]:
        return self.parser.get("RECAPTCHASECRET")

    def get_mailservice_secret_key(self) -> Optional[str]:
        return self.parser.get("MAILSERVICE_SECRET_KEY")

    def get_mailservice_salt(self) -> Optional[bytes]:
        return self.parser.get("MAILSERVICE_SALT")

    def get_sender_account(self) -> Optional[str]:
        # email address used in account management - 0 email - 1 pwd - 2 - dns - 3 port
        return self.parser.get("SENDER_ACCOUNT")

    def get_add_ticket(self) -> str:
        # string separator - separate  ticket number if ticket software is used and admin comment to user
        return str(self.parser.get("ADD_TICKET") or "").strip()

    def get_account_request_url(self) -> Optional[str]:
        # TODO find a way to have multi request url ( list of identified url ???)
        url = self.parser.get("SERVERURL", "").strip()
        return url + ("/" if url[-1] != "/" else "")

    def get_users_files_dir(self) -> Optional[str]:
        # My files service
        return self.parser.get("USERSFILESAREA", "").strip()

    def get_users_files_life(self) -> Optional[str]:
        # My files service
        return self.parser.get("TIMETOLIVE", "").strip()

    def get_cnf(self, key: str, default: Optional[str] = None) -> Optional[str]:
        # TODO: stop using so we can enumerate the keys
        return self.parser.get(key, default)

    def list_cnf(self) -> KeysView[str]:
        return self.parser.keys()

    def get_max_captcha_token_length(self) -> int:
        return int(self.parser.get("MAX_CAPTCHA_TOKEN_LENGTH", "4096"))
