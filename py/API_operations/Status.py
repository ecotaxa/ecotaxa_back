# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

from BO.Rights import RightsBO
from DB.User import Role, User, UserIDT
from helpers.AppConfig import ConfigKey, validate_directory
from .helpers.Service import Service


def _safe_call(getter: Callable[[], Any]) -> Any:
    try:
        return getter()
    except (AssertionError, ValueError):
        return None


def _format_bytes(num_bytes: int) -> str:
    size = float(num_bytes)
    for suffix in ("B", "K", "M", "G", "T"):
        if abs(size) < 1024.0:
            if suffix == "B":
                return f"{int(size)}B"
            return f"{size:.1f}{suffix}"
        size /= 1024.0
    return f"{size:.1f}P"


class StatusService(Service):
    """
    A utility service for ensuring the sanity of environment/config.
    Useful inside a docker container.
    """

    def __init__(self) -> None:
        super().__init__()

    def _dump_config(self, is_admin: bool) -> List[Tuple[ConfigKey, Any]]:
        entries: List[Tuple[ConfigKey, Any]] = []
        app_mgr = _safe_call(self.config.get_app_manager)
        if app_mgr is not None:
            entries.extend(
                [
                    (ConfigKey.APPMANAGER_NAME, app_mgr[0]),
                    (ConfigKey.APPMANAGER_EMAIL, app_mgr[1]),
                ]
            )
        if not is_admin:
            return entries

        db_addr = _safe_call(lambda: self.config.get_db_address(read_only=False))
        if db_addr is not None:
            entries.extend(
                [
                    (ConfigKey.DB_HOST, db_addr[0]),
                    (ConfigKey.DB_PORT, db_addr[1]),
                    (ConfigKey.DB_DATABASE, db_addr[2]),
                ]
            )
        db_creds = _safe_call(lambda: self.config.get_db_credentials(read_only=False))
        if db_creds is not None:
            entries.extend(
                [
                    (ConfigKey.DB_USER, db_creds[0]),
                    (ConfigKey.DB_PASSWORD, db_creds[1]),
                ]
            )
        ro_db_addr = _safe_call(lambda: self.config.get_db_address(read_only=True))
        if ro_db_addr is not None:
            entries.extend(
                [
                    (ConfigKey.RO_DB_HOST, ro_db_addr[0]),
                    (ConfigKey.RO_DB_PORT, ro_db_addr[1]),
                    (ConfigKey.RO_DB_DATABASE, ro_db_addr[2]),
                ]
            )
        ro_db_creds = _safe_call(lambda: self.config.get_db_credentials(read_only=True))
        if ro_db_creds is not None:
            entries.extend(
                [
                    (ConfigKey.RO_DB_USER, ro_db_creds[0]),
                    (ConfigKey.RO_DB_PASSWORD, ro_db_creds[1]),
                ]
            )

        single_getters: List[Tuple[ConfigKey, Callable[[], Any]]] = [
            (ConfigKey.INSTANCE_ID, self.config.get_instance_id),
            (ConfigKey.ALL_IN_ONE, self.config.get_all_in_one),
            (ConfigKey.THUMBSIZELIMIT, self.config.get_thumbnails_limit),
            (ConfigKey.VAULT_DIR, self.config.vault_dir),
            (ConfigKey.JOBS_DIR, self.config.jobs_dir),
            (ConfigKey.SERVERLOADAREA, self.config.common_folder),
            (ConfigKey.FTPEXPORTAREA, self.config.export_folder),
            (ConfigKey.MODELSAREA, self.config.models_dir),
            (ConfigKey.USERSFILESAREA, self.config.get_users_files_dir),
            (ConfigKey.DIR_MAIL_TEMPLATES, self.config.get_dir_mail_templates),
            (ConfigKey.TIMETOLIVE, self.config.get_time_to_live),
            (ConfigKey.MAX_UPLOAD_SIZE, self.config.get_max_upload_size),
            (ConfigKey.SECRET_KEY, self.config.secret_key),
            (ConfigKey.SECURITY_PASSWORD_HASH, self.config.get_security_password_hash),
            (ConfigKey.SECURITY_PASSWORD_SALT, self.config.get_security_password_salt),
            (
                ConfigKey.PASSWORD_SINGLE_HASH,
                lambda: ConfigKey.PASSWORD_SINGLE_HASH in self.config.list_cnf(),
            ),
            (ConfigKey.ACCESS_TOKEN_TTL, self.config.get_access_token_ttl),
            (ConfigKey.REFRESH_TOKEN_TTL, self.config.get_refresh_token_ttl),
            (ConfigKey.MAX_REFRESH_FAMILIES, self.config.get_max_refresh_families),
            (ConfigKey.LEGACY_TOKENS, self.config.get_legacy_tokens_on),
            (ConfigKey.RECAPTCHAID, self.config.get_recaptchaid),
            (ConfigKey.RECAPTCHASECRET, self.config.get_recaptchasecret),
            (
                ConfigKey.MAX_CAPTCHA_TOKEN_LENGTH,
                self.config.get_max_captcha_token_length,
            ),
            (
                ConfigKey.USER_EMAIL_VERIFICATION,
                self.config.get_user_email_verification,
            ),
            (ConfigKey.ACCOUNT_VALIDATION, self.config.get_account_validation),
            (ConfigKey.ADD_TICKET, self.config.get_add_ticket),
            (ConfigKey.SERVERURL, self.config.get_account_validation_url),
            (ConfigKey.MAILSERVICE_SECRET_KEY, self.config.get_mailservice_secret_key),
            (ConfigKey.MAILSERVICE_SALT, self.config.get_mailservice_salt),
            (ConfigKey.SENDER_ACCOUNT, self.config.get_sender_account),
            (ConfigKey.TAXOSERVER_URL, self.config.get_taxoserver_url),
            (ConfigKey.TAXOSERVER_INSTANCE_ID, self.config.get_taxoserver_instance_id),
            (
                ConfigKey.TAXOSERVER_SHARED_SECRET,
                self.config.get_taxoserver_shared_secret,
            ),
            (
                ConfigKey.OPENID_REQUIRE_VERIFIED_EMAIL,
                self.config.get_openid_require_verified_email,
            ),
            (ConfigKey.CORS_ALLOWED_ORIGINS, self.config.get_cors_allowed_origins),
            (
                ConfigKey.CORS_ALLOWED_ORIGIN_REGEX,
                self.config.get_cors_allowed_origin_regex,
            ),
            (ConfigKey.UNPACK_MIN_FREE_DISK, self.config.get_unpack_min_free_disk),
            (ConfigKey.MAX_UNPACK_ENTRIES, self.config.get_max_unpack_entries),
            (ConfigKey.MAX_UNPACKED_SIZE, self.config.get_max_unpacked_size),
            (ConfigKey.MAX_UNPACK_DEPTH, self.config.get_max_unpack_depth),
            (ConfigKey.UNPACK_SYNC_WAIT, self.config.get_unpack_sync_wait),
            (ConfigKey.APP_PORT, self.config.get_app_port),
            (ConfigKey.NO_TIME_LOG, self.config.get_no_time_log),
        ]
        for key, getter in single_getters:
            entries.append((key, _safe_call(getter)))

        openid_cfg = _safe_call(self.config.get_openid_config)
        if openid_cfg is not None:
            entries.extend(
                [
                    (ConfigKey.OPENID_CLIENT_ID, openid_cfg[0]),
                    (ConfigKey.OPENID_CLIENT_SECRET, openid_cfg[1]),
                    (ConfigKey.OPENID_METADATA_URL, openid_cfg[2]),
                ]
            )
        return entries

    def run(self, current_user_id: Optional[UserIDT]) -> str:
        """
        Produce the answer.
        """
        if current_user_id is None:
            return "UP!"
        # current_user = self.ro_session.get(User,current_user_id)
        current_user: Optional[User] = RightsBO.get_optional_user(
            self.ro_session, current_user_id
        )
        if current_user is None:
            return "Who?"
        is_admin = current_user.has_role(Role.APP_ADMINISTRATOR)
        ret = ["Config dump:"]
        for k, v in self._dump_config(is_admin):
            if "secret" in k.lower() or "salt" in k.lower() or "password" in k.lower():
                v = "*************"
            ret.append("  %s: %s" % (k, v))
        ret.append("Paths:")
        paths_in_conf: List[
            Tuple[ConfigKey, Callable[[], Optional[str]], bool, bool]
        ] = [
            (ConfigKey.VAULT_DIR, self.config.vault_dir, True, True),
            (ConfigKey.JOBS_DIR, self.config.jobs_dir, True, True),
            (ConfigKey.USERSFILESAREA, self.config.get_users_files_dir, True, True),
            (ConfigKey.MODELSAREA, self.config.models_dir, True, False),
            (ConfigKey.SERVERLOADAREA, self.config.common_folder, False, True),
            (ConfigKey.FTPEXPORTAREA, self.config.export_folder, True, False),
        ]
        for pk, getter, check_read, check_write in paths_in_conf:
            path_str = _safe_call(getter)
            if path_str is None or not path_str.strip("'"):
                ret.append("  %s not found" % pk)
                continue
            path = Path(path_str.strip("'"))
            try:
                free_space = validate_directory(
                    path, check_read=check_read, check_write=check_write
                )
                status = f"OK ({_format_bytes(free_space)} left)"
            except AssertionError:
                status = "*** KO ***"
            if not is_admin:
                path = Path("/somepath")
            ret.append("  %s (from %s): %s" % (path, pk, status))
        ret.append("")
        return "\n".join(ret)
