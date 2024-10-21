# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Send Account registration , status information and validation emails
#
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from enum import Enum
from typing import Optional, Final, Tuple, Dict, Any

from fastapi import HTTPException

from helpers import DateTime
from helpers.DynamicLogs import get_logger
from helpers.httpexception import (
    DETAIL_TEMPLATE_NOT_FOUND,
    DETAIL_INVALID_PARAMETER,
    DETAIL_INVALID_EMAIL,
    DETAIL_NO_RECIPIENT,
    DETAIL_SMTP_RECIPIENT_REFUSED,
    DETAIL_SMTP_DATA_ERROR,
    DETAIL_SMTP_DISCONNECT_ERROR,
    DETAIL_SMTP_CONNECT_ERROR,
    DETAIL_SMTP_RESPONSE_ERROR,
    DETAIL_IMAP4_ERROR,
    DETAIL_UNKNOWN_ERROR,
)

logger = get_logger(__name__)


class AccountMailType(str, Enum):
    activate: Final = "activate"
    verify: Final = "verify"
    status: Final = "status"
    modify: Final = "modify"
    password_reset: Final = "password_reset"


class ReplaceInMail:
    def __init__(
        self,
        email: Optional[str] = None,
        id: Optional[int] = None,
        action: Optional[str] = None,
        data: Optional[dict] = None,
        token: Optional[str] = None,
        reason: Optional[str] = None,
        url: Optional[str] = None,
        token_age: Optional[int] = None,
        ticket: Optional[str] = "",
    ):
        self.id = id
        # user id  - {id}
        self.email = email
        # "Email added in the template message body with the tag {email}
        self.data = data
        # Data to be included in the template message body with the tag {data} - if key data exists in the template it is replaced before
        self.token = token
        # token added to the link to verify the action - max_age :24h" - tag {token}
        self.action = action
        # update / verify / create - can indicate the status in some mails
        self.reason = reason
        # reason to request to modify information from user tag {reason}
        self.url = url
        # url of the requesting app - will be replaced in the mail message template
        self.token_age = token_age
        # token lifespan
        self.ticket = ticket
        # ticket number if provided


DEFAULT_LANGUAGE = "en_EN"


class MailProvider(object):
    """
    Tools to validate user registration and activation - send validation mails to external validation service - and change password service
    """

    MODEL_KEYS = ("email", "link", "action", "assistance", "reason")
    REPLACE_KEYS = ("token", "data", "url", "ticket", "reason")

    def __init__(
        self,
        sender_account: list,
        dir_mail_templates: str,
        short_token_age: Optional[int] = 1,
        profile_token_age: Optional[int] = 24,
        add_ticket: str = "",
    ):
        on = len(sender_account) > 2 and self.is_email(sender_account[0])
        if on:
            self.SENDER_ACCOUNT = sender_account
            self.DIR_MAIL_TEMPLATES = dir_mail_templates
            self.SHORT_TOKEN_AGE = short_token_age
            self.PROFILE_TOKEN_AGE = profile_token_age
            self.ADD_TICKET = add_ticket
            self.TICKET_MATCH = r"([)*([a-zA-Z])*(#)*([0-9])*(])"
        else:
            raise HTTPException(status_code=422, detail=[DETAIL_SMTP_DATA_ERROR])

    @staticmethod
    def is_email(email: str) -> bool:
        import re

        regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return re.match(regex, email) is not None

    def send_mail(
        self, recipients: list, msg: EmailMessage, reply_to: Optional[str] = None
    ) -> None:
        """
        Sendmail .
        """
        if self.SENDER_ACCOUNT is None:
            # make a response explaining why  the mail was not sent
            return
        for recipient in recipients:
            if not self.is_email(recipient):
                raise HTTPException(
                    status_code=422,
                    detail=[DETAIL_INVALID_EMAIL],
                )
        import email.utils as utils

        # starttls and 587  - with ssl 465
        # sender_account = self.SENDER_ACCOUNT
        # sender_email = sender_account[0].strip()
        # sender_pwd = sender_account[1].strip()
        # sender_dns = sender_account[2].strip()
        # sender_port = int(sender_account[3].strip())
        # imap_port = int(sender_account[4].strip())
        (
            sender_email,
            sender_pwd,
            sender_dns,
            sender_port,
            _,
        ) = self._extract_sender_account(self.SENDER_ACCOUNT)
        msg["From"] = sender_email
        msg["To"] = ", ".join(recipients)
        domain = sender_email.split("@")
        msg["message-id"] = utils.make_msgid(domain=domain[1])
        msg["Date"] = utils.formatdate()
        if reply_to == None:
            msg["Reply-To"] = "No-Reply"
        else:
            msg["Reply-To"] = str(reply_to)
        code = 0
        with smtplib.SMTP_SSL(sender_dns, sender_port) as smtp:
            try:
                smtp.login(sender_email, sender_pwd)
                # message as plain text
                smtp.sendmail(sender_email, recipients, msg.as_string())
                logger.info(
                    "Email subject %s sent  to '%s'"
                    % (msg["Subject"], ", ".join(recipients))
                )
            except smtplib.SMTPException as e:
                code, detail = self._log_smtp_error_code(e)
            except Exception as e:
                code, detail = self._log_error_code(e)
            finally:
                if code != 0:
                    raise HTTPException(
                        status_code=code,
                        detail=[detail],
                    )
                smtp.quit()

    @staticmethod
    def _log_error_code(e: Exception) -> Tuple[int, str]:
        code = 500
        detail = DETAIL_UNKNOWN_ERROR + ": '%s' , '%s'" % (type(e), e.args)
        logger.error(code, detail)
        return code, detail

    @staticmethod
    def _log_smtp_error_code(e: smtplib.SMTPException) -> Tuple[int, str]:
        if isinstance(e, smtplib.SMTPRecipientsRefused):
            code = 422
            detail = DETAIL_SMTP_RECIPIENT_REFUSED
        elif isinstance(e, smtplib.SMTPDataError):
            code = 422
            detail = DETAIL_SMTP_DATA_ERROR
        elif isinstance(e, smtplib.SMTPServerDisconnected):
            code = 500
            detail = DETAIL_SMTP_DISCONNECT_ERROR
        elif isinstance(e, smtplib.SMTPConnectError):
            code = 500
            detail = DETAIL_SMTP_CONNECT_ERROR
        elif isinstance(e, smtplib.SMTPResponseException):
            code = 500
            detail = DETAIL_SMTP_RESPONSE_ERROR
        else:
            code = 500
            detail = str(type(e)) + str(e.args)
        logger.error(e, detail)
        return code, detail

    def send_activation_request_mail(
        self,
        recipients: list,
        data: dict,
        action: str,
        token: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        if len(recipients) == 0:
            raise HTTPException(status_code=404, detail=[DETAIL_NO_RECIPIENT])
        user_id = data["id"]
        ticket = self._get_ticket(data["email"], user_id)
        replace = ReplaceInMail(
            id=user_id,
            email=data["email"],
            token=token,
            data=data,
            action=action,
            ticket=str(ticket or ""),
            url=url,
        )
        mail_msg = self._populate_mail_message(
            AccountMailType.activate, replace, action=action
        )
        self.send_mail(recipients, mail_msg, reply_to=data["email"])

    def send_verification_mail(
        self,
        recipient: str,
        assistance_email: str,
        token: str,
        action: Optional[str] = None,
        previous_email: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        data = ReplaceInMail(
            email=assistance_email, token=token, action=action, url=url
        )
        mail_msg = self._populate_mail_message(
            AccountMailType.verify,
            data,
            action=action,
            token_age=self.SHORT_TOKEN_AGE,
        )
        self.send_mail([recipient], mail_msg)
        # inform previous email (typo prevent)
        if previous_email is not None:
            data = ReplaceInMail(
                email=assistance_email, data={"new email": recipient}, url=url
            )
            mail_msg = self._populate_mail_message(
                AccountMailType.modify, data, action="inform"
            )
            self.send_mail([previous_email], mail_msg)

    def send_reset_password_mail(
        self,
        recipient: str,
        assistance_email: str,
        token: str,
        url: Optional[str] = None,
    ) -> None:
        data = ReplaceInMail(token=token, email=assistance_email, url=url)
        mail_msg = self._populate_mail_message(
            AccountMailType.password_reset, data, token_age=self.SHORT_TOKEN_AGE
        )
        self.send_mail([recipient], mail_msg)

    def send_status_mail(
        self,
        recipient: str,
        user_id: int,
        assistance_email: str,
        status_name: str,
        token: Optional[str] = None,
        reason: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        ticket = self._get_ticket(recipient, user_id)
        data = ReplaceInMail(
            email=assistance_email,
            token=token,
            token_age=self.PROFILE_TOKEN_AGE,
            reason=reason,
            ticket=str(ticket or ""),
            url=url,
        )
        mail_msg = self._populate_mail_message(
            AccountMailType.status, data, action=status_name
        )
        self.send_mail([recipient], mail_msg, reply_to=assistance_email)

    def send_has_to_modify_mail(
        self,
        recipient: str,
        assistance_email: str,
        user_id: int,
        reason: str,
        action: Optional[str] = None,
        token: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        """
        when there is a ticket software - ticket number can be found at the beginning of the comment/reason and sent back in the email subject
        """
        ticket = self._get_ticket(recipient, user_id)
        values = ReplaceInMail(
            email=assistance_email,
            reason=reason,
            token=token,
            url=url,
            token_age=self.PROFILE_TOKEN_AGE,
            ticket=str(ticket or ""),
        )
        mail_msg = self._populate_mail_message(
            AccountMailType.modify,
            values,
            action=action,
            token_age=self.PROFILE_TOKEN_AGE,
        )
        self.send_mail([recipient], mail_msg, reply_to=assistance_email)

    def _get_mail_message_throw(
        self,
        model_name: AccountMailType,
        language: str = DEFAULT_LANGUAGE,
        action: Optional[str] = None,
    ) -> dict:
        import json
        from pathlib import Path

        name = model_name.value + ".json"
        filename = Path(self.DIR_MAIL_TEMPLATES + "/" + name)
        if not filename.exists():
            raise HTTPException(
                status_code=404,
                detail=[DETAIL_TEMPLATE_NOT_FOUND],
            )
        with open(filename, "r") as f:
            model = json.load(f)
            f.close()
        if language in model.keys():
            model = dict(model[language])
        else:
            model = dict(model[DEFAULT_LANGUAGE])
        if action != None and action in model.keys():
            model = model[action]
        if model is None:
            raise HTTPException(
                status_code=422,
                detail=[DETAIL_INVALID_PARAMETER],
            )
        return model

    # tools to populate mail_message
    @staticmethod
    def _replace_dict_data_keys(key: str, model: dict, val: dict) -> str:
        if key in model:
            data = [model[key].format(key=k, value=v) for k, v in val.items()]
        else:
            data = [str(k) + " : " + str(v) for k, v in val.items()]
        return ",  ".join(data)

    def _replace_model_key(
        self, replace: dict, model: dict, values: ReplaceInMail
    ) -> Dict[Any, Any]:
        to_replace_keys = filter(lambda key: (key in model), self.MODEL_KEYS)
        for key in to_replace_keys:
            if key == "action" and getattr(values, key, None) is not None:
                replace[key] = model[key][getattr(values, key)]
            else:
                replace[key] = model[key].format(**vars(values))
        # more tolerant to errors in templates
        no_replace_keys = filter(lambda key: (key not in model), self.MODEL_KEYS)
        for key in no_replace_keys:
            replace[key] = ""
        return replace

    def _populate_mail_message(
        self,
        model_name: AccountMailType,
        values: ReplaceInMail,
        language: str = DEFAULT_LANGUAGE,
        action: Optional[str] = None,
        token_age: Optional[int] = None,
    ) -> EmailMessage:
        model = self._get_mail_message_throw(model_name, language, action=action)
        if "url" in model.keys():
            model_url = str(
                model["url"][1:] if model["url"][0] == "/" else model["url"]
            )
            values.url = str(values.url or "") + model_url
        replace: Dict[Any, Any] = {}
        replace = self._replace_model_key(replace, model, values)
        if "link" in replace:
            token_age = getattr(values, "token_age", token_age)
            if token_age is not None:
                age = DateTime.now_time() + timedelta(hours=int(token_age))
                ageval = age.strftime("%Y-%m-%d %H:%M:%S")
                replace["link"] += str(" (valid until %s (UTC))" % ageval)
        for rk in self.REPLACE_KEYS:
            if rk not in replace:
                if hasattr(values, rk):
                    replace[rk] = getattr(values, rk)
                else:
                    replace[rk] = ""
                continue
            val = getattr(values, rk, None)
            if val is None:
                continue
            if rk == "data":
                replace[rk] = self._replace_dict_data_keys(rk, model, val)
            else:
                replace[rk] = val
        mail_msg = EmailMessage()
        model["body"] = model["body"].format(**replace)
        mail_msg["Subject"] = model["subject"].format(
            action=str(action or ""),
            id=values.id,
            email=values.email,
            ticket=replace["ticket"],
        )
        text = html_to_text(model["body"])
        mail_msg.set_content(text, subtype="plain", charset="utf-8", cte="8bit")
        return mail_msg

    @staticmethod
    def _extract_sender_account(sender_account: list) -> tuple:
        # add default ports smtp and imap if not present
        if len(sender_account) == 3:
            sender_account.append("465")
        if len(sender_account) == 4:
            sender_account.append("993")
        return (
            sender_account[0].strip(),
            sender_account[1].strip(),
            sender_account[2].strip(),
            int(sender_account[3].strip()),
            int(sender_account[4].strip()),
        )

    def _get_ticket(
        self,
        user_email: str,
        user_id: int,
    ) -> Optional[str]:
        """Get ticket number from mailbox or status_admin_comment or token"""
        if self.ADD_TICKET == "":
            return None
        from itertools import chain
        import email
        import imaplib

        (
            sender_email,
            sender_pwd,
            sender_dns,
            _,
            imap_port,
        ) = self._extract_sender_account(self.SENDER_ACCOUNT)
        ticket = None
        try:
            # set connection
            mail = imaplib.IMAP4_SSL(sender_dns, imap_port)
            # login
            mail.login(sender_email, sender_pwd)
            # select inbox
            mail.select("INBOX")
            criteria = {
                "FROM": self.ADD_TICKET,
                "SUBJECT": str(user_id) + "#" + user_email + "#",
            }

            def search_string(criteria):
                c = list(map(lambda t: (t[0], '"' + str(t[1]) + '"'), criteria.items()))
                s = "(%s)" % " ".join(chain(*c))
                return s

            (_, data) = mail.uid("search", search_string(criteria))
            if data != None and isinstance(data, list):
                inbox_item_list = data[0].split()
                if len(inbox_item_list) > 0:
                    most_recent = inbox_item_list[-1]
                    _, email_data = mail.uid("fetch", most_recent, "(RFC822)")
                    raw_email = email_data[0][1].decode("UTF-8")
                    email_message = email.message_from_string(raw_email)
                    if "Subject" in email_message:
                        import re

                        match = re.match(self.TICKET_MATCH, email_message["Subject"])
                        if match:
                            ticket = match.group(0)
            mail.logout()
        except imaplib.IMAP4.error as e:
            code = 422
            detail = DETAIL_IMAP4_ERROR + str(e.args)
            logger.info(code, detail)
        except Exception as e:
            _, _ = self._log_error_code(e)

        return ticket


def html_to_text(html: str) -> str:
    import re

    html = html.replace("<br>", "\n")
    patterns = re.compile("<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});")
    return re.sub(patterns, "", html)
