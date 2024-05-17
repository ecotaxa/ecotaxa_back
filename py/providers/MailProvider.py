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
        self.tokenage = tokenage
        # token lifespan
        self.ticket = ticket
        # ticket number if provided


DEFAULT_LANGUAGE = "en_EN"


class MailProvider(object):
    """
    Tools to validate user registration and activation - send validation mails to external validation service - and change password service
    """

    MODEL_KEYS = ("email", "link", "action", "assistance", "reason")
    REPLACE_KEYS = ("token", "data", "url", "ticket")

    def __init__(
        self,
        senderaccount: list,
        dir_mail_templates: str,
        short_token_age: Optional[int] = 1,
        profile_token_age: Optional[int] = 24,
        add_ticket: str = "",
    ):
        on = len(senderaccount) > 2 and self.is_email(senderaccount[0])
        if on:
            self.SENDER_ACCOUNT = senderaccount
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
                raise HTTPException(
                    status_code=422,
                    detail=[DETAIL_INVALID_EMAIL],
                )
        import smtplib, ssl
        import email.utils as utils

        # starttls and 587  - avec ssl 465
        # senderaccount = self.SENDER_ACCOUNT
        # senderemail = senderaccount[0].strip()
        # senderpwd = senderaccount[1].strip()
        # senderdns = senderaccount[2].strip()
        # senderport = int(senderaccount[3].strip())
        (
            senderemail,
            senderpwd,
            senderdns,
            senderport,
            imapport,
        ) = self.extract_senderaccount()
        msg["From"] = senderemail
        msg["To"] = ", ".join(recipients)
        domain = senderemail.split("@")
        msg["message-id"] = utils.make_msgid(domain=domain[1])
        msg["Date"] = utils.formatdate()
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
                    code = 422
                    detail = DETAIL_SMTP_RECIPIENT_REFUSED
                elif isinstance(e, smtplib.SMTPDataError):
                    code = 422
                    detail = DETAIL_SMTP_DATA_ERROR
                else:
                    code = 500
                    detail = str(e.args)
                logger.error(e)
            except:
                code = 500
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
                status_code=422,
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
                            " (valid until %s (UTC))"
                            % age.strftime("%Y-%m-%d %H:%M:%S")
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
        mailmsg["Subject"] = model["subject"].format(
            action=replace["action"],
            id=values.id,
            email=values.email,
            ticket=replace["ticket"],
        )
        text = self.html_to_text(model["body"])
        mailmsg.set_content(text, subtype="plain", charset="utf-8", cte="8bit")
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
            raise HTTPException(status_code=404, detail=[DETAIL_NO_RECIPIENT])
        id = data["id"]
        ticket = self.get_ticket(data["email"], id)
        replace = ReplaceInMail(
            id=id,
            email=data["email"],
            token=token,
            data=data,
            action=action,
            ticket=str(ticket or ""),
            url=url,
        )
        mailmsg = self.mail_message(AccountMailType.activate, replace)
        self.send_mail(recipients, mailmsg, replyto=data["email"])

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
        self.send_mail([recipient], mailmsg)
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
        id: int,
        assistance_email: str,
        status_name: str,
        action: str,
        token: Optional[str] = None,
        reason: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        ticket = self.get_ticket(recipient, id)
        data = ReplaceInMail(
            email=assistance_email,
            token=token,
            tokenage=self.PROFILE_TOKEN_AGE,
            ticket=str(ticket or ""),
            url=url,
        )
        mailmsg = self.mail_message(AccountMailType.status, data, action=status_name)
        self.send_mail([recipient], mailmsg, replyto=assistance_email)

    def send_hastomodify_mail(
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
        ticket = self.get_ticket(recipient, user_id, reason, token)
        values = ReplaceInMail(
            email=assistance_email,
            reason=reason,
            token=token,
            url=url,
            tokenage=self.PROFILE_TOKEN_AGE,
            ticket=str(ticket or ""),
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
            return model[action]
        else:
            return model
        return None

    def extract_senderaccount(self) -> tuple:
        senderaccount = self.SENDER_ACCOUNT
        # add default ports smtp and imap if not present
        if len(senderaccount) == 3:
            senderaccount.append("465")
        if len(senderaccount) == 4:
            senderaccount.append("993")
        return (
            senderaccount[0].strip(),
            senderaccount[1].strip(),
            senderaccount[2].strip(),
            int(senderaccount[3].strip()),
            int(senderaccount[4].strip()),
        )

    def get_ticket(
        self,
        user_email: str,
        user_id: int,
        token: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Optional[str]:
        """Get ticket number from mailbox or status_admin_comment or token"""
        if self.ADD_TICKET == "":
            return None
        from itertools import chain
        import email
        import imaplib

        (
            senderemail,
            senderpwd,
            senderdns,
            senderport,
            imapport,
        ) = self.extract_senderaccount()
        ticket = None
        try:
            # set connection
            mail = imaplib.IMAP4_SSL(senderdns, imapport)
            # login
            mail.login(senderemail, senderpwd)
            # select inbox
            mail.select("INBOX")
            criteria = {
                "FROM": "Ecotaxa",
                "SUBJECT": str(user_id) + "#" + user_email + "#",
            }

            def search_string(criteria):
                c = list(map(lambda t: (t[0], '"' + str(t[1]) + '"'), criteria.items()))
                s = "(%s)" % " ".join(chain(*c))
                return s

            (_, data) = mail.uid("search", search_string(criteria))
            if data != None and isinstance(data, list):
                inbox_item_list = data[0].split()
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
        except:
            pass
        return ticket
