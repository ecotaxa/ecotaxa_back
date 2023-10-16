# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Maintenance operations on the DB.
#
from datetime import datetime, timedelta
from typing import Optional, Final
from enum import Enum
from helpers.DynamicLogs import get_logger
from helpers.pydantic import BaseModel, Field
from email.message import EmailMessage
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_404_NOT_FOUND,
)
from fastapi import HTTPException
from helpers.httpexception import (
    DETAIL_INVALID_EMAIL,
    DETAIL_NO_RECIPIENT,
    DETAIL_TEMPLATE_NOT_FOUND,
    DETAIL_INVALID_PARAMETER,
    DETAIL_SMTP_RECIPIENT_REFUSED,
    DETAIL_SMTP_DATA_ERROR,
    DETAIL_UNKNOWN_ERROR,
)

logger = get_logger(__name__)
# special token - only for mail - separate from auth token


class AccountMailType(str, Enum):
    activate: Final = "activate"
    verify: Final = "verify"
    status: Final = "status"
    modify: Final = "modify"
    passwordreset: Final = "passwordreset"


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
        tokenage: Optional[int] = None,
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
        self.tokenage = tokenage
        # token lifespan


DEFAULT_LANGUAGE = "en_EN"


class MailProvider(object):
    """
    Tools to validate user registration and activation - send validation mails to external validation service - and change password service
    """

    MODEL_KEYS = ("email", "link", "action", "assistance", "reason")
    REPLACE_KEYS = ("token", "data", "url")

    def __init__(
        self,
        senderaccount: list,
        dir_mail_templates: str,
        short_token_age: Optional[int] = 1,
        profile_token_age: Optional[int] = 24,
    ):
        on = len(senderaccount) == 4 and self.is_email(senderaccount[0])
        if on:
            from API_operations.CRUD import Users

            self.SENDER_ACCOUNT = senderaccount
            self.DIR_MAIL_TEMPLATES = dir_mail_templates
            self.SHORT_TOKEN_AGE = short_token_age
            self.PROFILE_TOKEN_AGE = profile_token_age

    @staticmethod
    def is_email(email: str) -> bool:
        import re

        regex = re.compile(
            "(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21\\x23-\\x5b\\x5d-\\x7f]|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21-\\x5a\\x53-\\x7f]|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])+)\\])"
        )
        return re.fullmatch(regex, email) is not None

    def send_mail(
        self, recipients: list, msg: EmailMessage, replyto: Optional[str] = None
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
                    detail=[DETAIL_INVALID_EMAIL],
                )
        import smtplib, ssl

        # starttls and 587  - avec ssl 465
        senderaccount = self.SENDER_ACCOUNT
        senderemail = senderaccount[0].strip()
        senderpwd = senderaccount[1].strip()
        senderdns = senderaccount[2].strip()
        senderport = int(senderaccount[3].strip())
        msg["From"] = senderemail
        msg["To"] = ", ".join(recipients)
        if replyto == None:
            msg["Reply-To"] = "No-Reply"
        else:
            msg["Reply-To"] = str(replyto)
        code = 0
        with smtplib.SMTP_SSL(senderdns, senderport) as smtp:
            try:
                smtp.login(senderemail, senderpwd)
                # message as plain text
                smtp.sendmail(senderemail, recipients, msg.as_string())
                logger.info(
                    "Email subject %s sent  to '%s'"
                    % (msg["Subject"], ", ".join(recipients))
                )
            except smtplib.SMTPException as e:
                if isinstance(e, smtplib.SMTPRecipientsRefused):
                    code = HTTP_422_UNPROCESSABLE_ENTITY
                    detail = DETAIL_SMTP_RECIPIENT_REFUSED
                elif isinstance(e, smtplib.SMTPDataError):
                    code = HTTP_422_UNPROCESSABLE_ENTITY
                    detail = DETAIL_SMTP_DATA_ERROR
                else:
                    code = HTTP_500_INTERNAL_SERVER_ERROR
                    detail = str(e.args)
                logger.error(e)
            except:
                code = HTTP_500_INTERNAL_SERVER_ERROR
                import sys

                detail = DETAIL_UNKNOWN_ERROR + ": '%s'" % sys.exc_info()[0]
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
        values: ReplaceInMail,
        language: str = DEFAULT_LANGUAGE,
        action: Optional[str] = None,
    ) -> EmailMessage:
        model: Optional[dict] = self.get_mail_message(model_name, language, action)
        if model is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[DETAIL_INVALID_PARAMETER],
            )
        replace = dict({})
        if "url" in model.keys():
            modelurl = str(model["url"][1:] if model["url"][0] == "/" else model["url"])
            if values.url is not None:
                values.url += modelurl
            else:
                values.url = modelurl
        for key in self.MODEL_KEYS:
            replace[key] = ""
            if key in model:
                if (
                    key == "action"
                    and hasattr(values, key)
                    and getattr(values, key) is not None
                ):
                    replace[key] = model[key][getattr(values, key)]
                else:
                    replace[key] = model[key].format(**vars(values))
                    # add info about max_age of the token
                    if (
                        key == "link"
                        and hasattr(values, "token")
                        and getattr(values, "token") is not None
                    ):
                        if (
                            hasattr(values, "tokenage")
                            and getattr(values, "tokenage") is not None
                        ):
                            tokenage = getattr(values, "tokenage")
                        else:
                            tokenage = self.SHORT_TOKEN_AGE
                        age = datetime.now() + timedelta(hours=int(tokenage))
                        replace[key] += str(
                            " (valid until %s-%s-%s, %s:%s)"
                            % (
                                age.year,
                                age.month,
                                age.day,
                                age.hour,
                                age.minute,
                            )
                        )

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
        mailmsg = EmailMessage()
        mailmsg["Subject"] = model["subject"].format(action=replace["action"])
        text = self.html_to_text(model["body"])
        mailmsg.set_content(text, subtype="plain", charset="utf-8")
        return mailmsg

    @staticmethod
    def html_to_text(html: str) -> str:
        import re

        html = re.sub("<br>", "\n", html)
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
                status_code=HTTP_404_NOT_FOUND, detail=[DETAIL_NO_RECIPIENT]
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
        mailmsg = self.mail_message(AccountMailType.activate, replace)
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
        mailmsg = self.mail_message(AccountMailType.verify, data, action=action)
        self.send_mail([recipient], mailmsg, replyto=assistance_email)
        # inform previous email (typo prevent)
        if previous_email is not None:
            data = ReplaceInMail(
                email=assistance_email, data={"new email": recipient}, url=url
            )
            mailmsg = self.mail_message(AccountMailType.modify, data, action="inform")
            self.send_mail([previous_email], mailmsg)

    def send_reset_password_mail(
        self,
        recipient: str,
        assistance_email: str,
        token: str,
        url: Optional[str] = None,
    ) -> None:
        data = ReplaceInMail(token=token, email=assistance_email, url=url)
        mailmsg = self.mail_message(AccountMailType.passwordreset, data)
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
        data = ReplaceInMail(
            email=assistance_email, token=token, tokenage=self.PROFILE_TOKEN_AGE
        )
        mailmsg = self.mail_message(AccountMailType.status, data, action=status_name)
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
            tokenage=self.PROFILE_TOKEN_AGE,
        )
        mailmsg = self.mail_message(AccountMailType.modify, values, action=action)
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
            return model[action]
        else:
            return model
        return None
