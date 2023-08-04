# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Maintenance operations on the DB.
#
import datetime
from typing import Optional, Any
from helpers.DynamicLogs import get_logger, LogsSwitcher
from helpers.pydantic import BaseModel, Field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from providers.Google import ReCAPTCHAClient
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
)
from API_models.crud import MinUserModel
from fastapi import HTTPException


logger = get_logger(__name__)
# special token - only for mail - separate from auth token


class ReplaceInMail(BaseModel):
    id: Optional[int] = Field(
        title="User Id", description="User unique identifier.", example=1, default=None
    )
    email: Optional[str] = Field(
        title="email to reply",
        description="Email added at the end of the message",
        default=None,
    )
    data: Optional[dict] = Field(
        title="Data",
        description="Data to be included in the message",
        example={"name": "name", "email": "test@mail.com"},
        default=None,
    )
    action: Optional[str] = Field(
        title="Action", description="Create or Update", default=None
    )

    token: Optional[str] = Field(
        title="Token",
        description="token added to the link to verify the action - max_age :24h",
        default=None,
    )
    url: Optional[str] = Field(
        title="URL",
        description="url of the requesting app - will be replaced in the mail message template",
        default=None,
    )


DEFAULT_LANGUAGE = "en_EN"


class MailProvider(object):
    """
    Tools to validate user registration and activation - send validation mails to external validation service - and change password service
    """

    PATH_MAIL_TEMPLATE = "templates/mails/{name}.json"
    MODEL_ACTIVATE = "activate"
    MODEL_VERIFY = "verify"
    MODEL_ACTIVATED = "active"
    MODEL_KEYS = [
        "email",
        "link",
        "action",
    ]
    REPLACE_KEYS = ["id", "token", "data", "url"]
    MODEL_PASSWORD_RESET = "passwordreset"
    ACTIVATION_ACTION_CREATE = "create"
    ACTIVATION_ACTION_UPDATE = "update"
    ACTIVATION_ACTION_ACTIVE = "active"
    ACTIVATION_ACTION_DESACTIVE = "desactive"

    def __init__(self, senderaccount: list, account_activate_email: str):
        self.on = len(senderaccount) == 4 and self.is_email(senderaccount[0])
        self.account_activate_email = account_activate_email
        self.senderaccount = senderaccount

    def __call__(self) -> Optional[object]:
        if self.on:
            return self
        return None

    @staticmethod
    def is_email(email: str) -> bool:
        import re

        regex = re.compile(
            r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+"
        )
        return re.fullmatch(regex, email) is not None

    def send_mail(
        self, email: str, msg: MIMEMultipart, replyto: Optional[str] = None
    ) -> None:
        """
        Sendmail .
        """
        if not self.is_email(email):
            HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=["Not an email address"],
            )
        import smtplib, ssl

        # starttls and 587  - avec ssl 465
        senderaccount = self.senderaccount
        senderemail = senderaccount[0].strip()
        senderpwd = senderaccount[1].strip()
        senderdns = senderaccount[2].strip()
        senderport = int(senderaccount[3].strip())
        msg["From"] = senderemail
        recipients = [email]
        if replyto != None:
            msg.add_header("reply-to", str(replyto))
        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(senderdns, senderport, context=context) as smtp:
                smtp.login(senderemail, senderpwd)
                try:
                    res = smtp.sendmail(senderemail, recipients, msg.as_string())
                except smtplib.SMTPRecipientsRefused:
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=["invalid email"],
                    )
                smtp.quit()
                if res == {}:
                    logger.info("Email sent  to '%s'" % email)
        except:
            logger.info("Email not sent to '%s'" % email)
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Mail not sent",
            )

    def mail_message(
        self,
        model_name: str,
        recipients: list,
        values: dict,
        language: str = DEFAULT_LANGUAGE,
        action: Optional[str] = None,
    ) -> MIMEMultipart:
        model = self.get_mail_message(model_name, language, action)
        values = dict(values)
        replace = dict({})
        for key in self.MODEL_KEYS:
            replace[key] = ""
            if key in model.keys():
                if (
                    key == "link"
                    and (
                        "url" not in values.keys()
                        or values["url"] is None
                        or values["url"].strip() == ""
                    )
                    and "url" in model.keys()
                ):
                    values["url"] = model["url"]
                if key in values.keys() and key == "action":
                    replace[key] = model[key][values[key]]
                else:
                    replace[key] = model[key].format(**values)
        for key in self.REPLACE_KEYS:
            if key in values.keys():
                if key == "data" and type(values["data"]) == "dict":
                    data = []
                    for k, v in values["data"].items():
                        data.append(model["data"].format(key=k, value=v))
                replace[key] = values[key]
            elif key not in replace.keys():
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

    def send_activation_mail(
        self,
        recipient: str,
        data: dict,
        token: Optional[str] = None,
        action: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        if recipient == None:
            return
        if action is None:
            action = self.ACTIVATION_ACTION_CREATE
        replace = ReplaceInMail(
            id=data["id"],
            email=data["email"],
            token=token,
            data=data,
            action=action,
            url=url,
        )

        mailmsg = self.mail_message(self.MODEL_ACTIVATE, [recipient], replace.__dict__)
        self.send_mail(recipient, mailmsg)

    def send_verification_mail(
        self,
        recipient: str,
        token: str,
        action: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        reply_to = self.get_assistance_mail()
        data = ReplaceInMail(email=reply_to, token=token, action=action, url=url)
        mailmsg = self.mail_message(
            self.MODEL_VERIFY, [recipient], data.__dict__, action=action
        )
        self.send_mail(recipient, mailmsg, replyto=reply_to)

    def send_reset_password_mail(
        self, recipient: str, token: str, url: Optional[str] = None
    ) -> None:
        assistance_email = self.get_assistance_mail()
        data = ReplaceInMail(token=token, email=assistance_email, url=url)
        mailmsg = self.mail_message(
            self.MODEL_PASSWORD_RESET, [recipient], data.__dict__
        )
        self.send_mail(recipient, mailmsg)

    def send_desactivated_mail(self, recipient: str) -> None:
        self.send_activated_mail(recipient, False)

    def send_activated_mail(
        self,
        recipient: str,
        active: bool = True,
        action: Optional[str] = None,
        token: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        assistance_email = self.get_assistance_mail()
        data = ReplaceInMail(email=assistance_email, token=token)
        mailmsg = self.mail_message(
            self.MODEL_ACTIVATED, [recipient], data.__dict__, action=action
        )
        self.send_mail(recipient, mailmsg, replyto=assistance_email)

    def send_hastomodify_mail(
        self,
        recipient: str,
        reason: str,
        action: Optional[str] = None,
        token: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        assistance_email = self.get_assistance_mail()
        data = ReplaceInMail(
            email=assistance_email, data={"reason": reason}, token=token, url=url
        )
        mailmsg = self.mail_message(
            self.MODEL_ACTIVATED, [recipient], data.__dict__, action=action
        )
        self.send_mail(recipient, mailmsg, replyto=assistance_email)

    def get_mail_message(
        self, model_name: str, language, action: Optional[str] = None
    ) -> dict:
        import json

        filename = self.PATH_MAIL_TEMPLATE.format(name=model_name)
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

    def get_assistance_mail(self) -> Optional[str]:
        assistance_email: Optional[str] = self.account_activate_email
        if assistance_email == None:
            from API_operations.CRUD.Users import UserService

            with UserService() as sce:
                users_admins = sce.get_users_admins()
            if len(users_admins):
                return users_admins[0].email
        return assistance_email
