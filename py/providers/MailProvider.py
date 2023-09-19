# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Maintenance operations on the DB.
#
import datetime
from typing import Optional, Final
from enum import Enum
from helpers.DynamicLogs import get_logger
from helpers.pydantic import BaseModel, Field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_404_NOT_FOUND,
)
from fastapi import HTTPException

logger = get_logger(__name__)
# special token - only for mail - separate from auth token


class AccountMailType(str, Enum):
    activate: Final = "activate"
    verify: Final = "verify"
    status: Final = "status"
    modify: Final = "modify"
    passwordreset: Final = "passwordreset"
    emailmodified: Final = "emailmodified"


# replace in mail templates
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


DEFAULT_LANGUAGE = "en_EN"


class MailProvider(object):
    """
    Tools to validate user registration and activation - send validation mails to external validation service - and change password service
    """

    MODEL_KEYS = ("email", "link", "action", "assistance")
    REPLACE_KEYS = ("token", "data", "url", "reason")

    def __init__(
        self,
        senderaccount: list,
        dir_mail_templates: str,
    ):
        on = len(senderaccount) == 4 and self.is_email(senderaccount[0])
        if on:
            from API_operations.CRUD import Users

            self.SENDER_ACCOUNT = senderaccount
            self.DIR_MAIL_TEMPLATES = dir_mail_templates

    @staticmethod
    def is_email(email: str) -> bool:
        import re

        regex = re.compile(
            r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+"
        )
        return re.fullmatch(regex, email) is not None

    def send_mail(
        self, recipients: list, msg: MIMEMultipart, replyto: Optional[str] = None
    ) -> None:
        """
        Sendmail .
        """
        if self.SENDER_ACCOUNT is None:
            # make a response explaining why  the mail was not sent
            return
        for recipient in recipients:
            if not self.is_email(recipient):
                HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=["Not an email address"],
                )
        import smtplib, ssl

        # starttls and 587  - avec ssl 465
        senderaccount = self.SENDER_ACCOUNT
        senderemail = senderaccount[0].strip()
        senderpwd = senderaccount[1].strip()
        senderdns = senderaccount[2].strip()
        senderport = int(senderaccount[3].strip())
        msg["From"] = senderemail
        if replyto != None:
            msg.add_header("reply-to", str(replyto))
        code = 0
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(senderdns, senderport, context=context) as smtp:
            try:
                smtp.login(senderemail, senderpwd)
                res = smtp.sendmail(senderemail, recipients, msg.as_string())
                # res = smtp.send_message(msg)
                logger.info(
                    "Email subject %s sent  to '%s'"
                    % (msg["Subject"], ", ".join(recipients))
                )
            except smtplib.SMTPException as e:
                if isinstance(e, smtplib.SMTPRecipientsRefused):
                    code = HTTP_422_UNPROCESSABLE_ENTITY
                    detail = "Recipient refused"
                elif isinstance(e, smtplib.SMTPDataError):
                    code = HTTP_422_UNPROCESSABLE_ENTITY
                    detail = "Data error"
                else:
                    code = HTTP_500_INTERNAL_SERVER_ERROR
                    detail = str(e.args)
                logger.error(e)
            except:
                code = HTTP_500_INTERNAL_SERVER_ERROR
                import sys

                detail = "Unknown error: '%s'" % sys.exc_info()[0]
                logger.error(code, detail)
            finally:
                if code != 0:
                    raise HTTPException(
                        status_code=code,
                        detail=[detail],
                    )
                smtp.quit()

    def mail_message(
        self,
        model_name: AccountMailType,
        recipients: list,
        values: ReplaceInMail,
        language: str = DEFAULT_LANGUAGE,
        action: Optional[str] = None,
    ) -> MIMEMultipart:
        model: Optional[dict] = self.get_mail_message(model_name, language, action)
        if model is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=["type of email not found"],
            )
        replace = dict({})
        for key in self.MODEL_KEYS:
            replace[key] = ""
            if key in model:
                if (
                    key == "link"
                    and (
                        not hasattr(values, "url")
                        or values.url is None
                        or values.url.strip() == ""
                    )
                    and "url" in model
                ):
                    values.url = model["url"]
                if (
                    (key == "action")
                    and hasattr(values, key)
                    and getattr(values, key) is not None
                ):
                    replace[key] = model[key][getattr(values, key)]
                else:
                    replace[key] = model[key].format(**vars(values))
        for key in self.REPLACE_KEYS:
            if hasattr(values, key):
                if (
                    key == "data"
                    and values.data is not None
                    and type(values.data) is dict
                ):
                    data = []
                    if key in model:
                        for k, v in values.data.items():
                            data.append(model["data"].format(key=k, value=v))

                    else:
                        for k, v in values.data.items():
                            data.append(str(k) + " : " + str(v))
                    replace[key] = ",  ".join(data)
                else:
                    replace[key] = getattr(values, key)
            elif key not in replace:
                replace[key] = ""

        model["body"] = model["body"].format(**replace)
        mailmsg = MIMEMultipart("alternative")
        mailmsg["Subject"] = model["subject"].format(action=replace["action"])
        mailmsg["To"] = ", ".join(recipients)
        html = model["body"]
        text = self.html_to_text(html)
        mailmsg.attach(MIMEText(text, "plain"))
        mailmsg.attach(MIMEText(html, "html"))
        return mailmsg

    @staticmethod
    def html_to_text(html: str) -> str:
        import re

        pattrns = re.compile("<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});")
        return re.sub(pattrns, "", html)

    def send_activation_request_mail(
        self,
        recipients: list,
        data: dict,
        action: str,
        token: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        if len(recipients) == 0:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=["Users admin not found"]
            )
        id = data["id"]
        replace = ReplaceInMail(
            id=id,
            email=data["email"],
            token=token,
            data=data,
            action=action,
            url=url,
        )
        mailmsg = self.mail_message(AccountMailType.activate, recipients, replace)
        self.send_mail(recipients, mailmsg)

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
        mailmsg = self.mail_message(
            AccountMailType.verify, [recipient], data, action=action
        )
        self.send_mail([recipient], mailmsg, replyto=assistance_email)
        # inform previous email (typo prevent)
        if previous_email is not None:
            data = ReplaceInMail(email=assistance_email, reason=recipient, url=url)
            mailmsg = self.mail_message(
                AccountMailType.emailmodified, [previous_email], data
            )
            self.send_mail([previous_email], mailmsg, replyto=assistance_email)

    def send_reset_password_mail(
        self,
        recipient: str,
        assistance_email: str,
        token: str,
        url: Optional[str] = None,
    ) -> None:
        data = ReplaceInMail(token=token, email=assistance_email, url=url)
        mailmsg = self.mail_message(AccountMailType.passwordreset, [recipient], data)
        self.send_mail([recipient], mailmsg)

    def send_status_mail(
        self,
        recipient: str,
        assistance_email: str,
        status_name: str,
        action: str,
        token: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        data = ReplaceInMail(email=assistance_email, token=token)
        mailmsg = self.mail_message(
            AccountMailType.status, [recipient], data, action=status_name
        )

        self.send_mail([recipient], mailmsg, replyto=assistance_email)

    def send_hastomodify_mail(
        self,
        recipient: str,
        assistance_email: str,
        reason: str,
        action: Optional[str] = None,
        token: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        values = ReplaceInMail(
            email=assistance_email,
            reason=reason,
            token=token,
            url=url,
        )

        mailmsg = self.mail_message(
            AccountMailType.modify, [recipient], values, action=action
        )
        self.send_mail([recipient], mailmsg, replyto=assistance_email)

    def get_mail_message(
        self, model_name: AccountMailType, language, action: Optional[str] = None
    ) -> Optional[dict]:
        import json
        from pathlib import Path

        name = model_name.value + ".json"

        filename = Path(self.DIR_MAIL_TEMPLATES + "/" + name)
        if not filename.exists():
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=["model of email response not found"],
            )
        with open(filename, "r") as f:
            model = json.load(f)
            f.close()
        if language in model.keys():
            model = dict(model[language])
        else:
            model = dict(model[DEFAULT_LANGUAGE])
        if action != None and action in model.keys():
            return model[action]
        else:
            return model
        return None
