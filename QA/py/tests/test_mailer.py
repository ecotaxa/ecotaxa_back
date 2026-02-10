# -*- coding: utf-8 -*-
# Tests for providers.MailProvider methods using pytest-mock

import imaplib
import smtplib
from email.message import EmailMessage

import pytest
from fastapi import HTTPException

from helpers.httpexception import (
    DETAIL_SMTP_RECIPIENT_REFUSED,
    DETAIL_SMTP_DATA_ERROR,
    DETAIL_SMTP_DISCONNECT_ERROR,
    DETAIL_SMTP_CONNECT_ERROR,
    DETAIL_SMTP_RESPONSE_ERROR,
)
from providers.MailProvider import MailProvider

VALID_SENDER_ACCOUNT = [
    "sender@example.com",
    "secret_pwd",
    "smtp.example.com",
    "465",
]


def make_provider():
    # dir_mail_templates is not used by send_mail; provide any string
    return MailProvider(VALID_SENDER_ACCOUNT[:], dir_mail_templates="/tmp")


def test_send_mail_returns_early_when_sender_account_none(mocker):
    # Arrange
    provider = make_provider()
    # Force guard clause path
    provider.SENDER_ACCOUNT = None

    smtp_cls = mocker.patch("smtplib.SMTP_SSL")

    msg = EmailMessage()
    msg["Subject"] = "Test"
    msg.set_content("Body")

    # Act: should return early and never touch SMTP
    provider.send_mail(["to@example.com"], msg)

    # Assert
    smtp_cls.assert_not_called()


def test_send_mail_success_sends_and_quits(mocker):
    # Arrange
    provider = make_provider()

    smtp_cls = mocker.patch("smtplib.SMTP_SSL")
    mock_smtp = mocker.Mock()
    smtp_cls.return_value.__enter__.return_value = mock_smtp

    msg = EmailMessage()
    msg["Subject"] = "Hello"
    msg.set_content("Hi there")

    recipients = ["to1@example.com", "to2@example.com"]

    # Act: no exception expected
    provider.send_mail(recipients, msg)

    # Assert: login, sendmail and quit called with expected parameters
    sender_email = VALID_SENDER_ACCOUNT[0]
    sender_pwd = VALID_SENDER_ACCOUNT[1]

    mock_smtp.login.assert_called_once_with(sender_email, sender_pwd)
    mock_smtp.sendmail.assert_called_once()
    # Check sendmail args basics
    args, kwargs = mock_smtp.sendmail.call_args
    assert args[0] == sender_email
    assert args[1] == recipients
    assert isinstance(args[2], str)  # msg.as_string()

    mock_smtp.quit.assert_called_once()


@pytest.mark.parametrize(
    "smtp_exception, expected_code, expected_detail",
    [
        (
            smtplib.SMTPRecipientsRefused(recipients={}),
            422,
            DETAIL_SMTP_RECIPIENT_REFUSED,
        ),
        (smtplib.SMTPDataError(code=550, msg="error"), 422, DETAIL_SMTP_DATA_ERROR),
        (smtplib.SMTPServerDisconnected(), 500, DETAIL_SMTP_DISCONNECT_ERROR),
        (
            smtplib.SMTPConnectError(code=500, msg="error"),
            500,
            DETAIL_SMTP_CONNECT_ERROR,
        ),
        (
            smtplib.SMTPResponseException(code=500, msg="error"),
            500,
            DETAIL_SMTP_RESPONSE_ERROR,
        ),
        (smtplib.SMTPException("Generic SMTP error"), 500, "Generic SMTP error"),
    ],
)
def test_send_mail_raises_http_exception_on_smtp_exception(
    mocker, smtp_exception, expected_code, expected_detail
):
    # Arrange
    provider = make_provider()

    smtp_cls = mocker.patch("smtplib.SMTP_SSL")
    mock_smtp = mocker.Mock()
    smtp_cls.return_value.__enter__.return_value = mock_smtp

    # Make sendmail raise the specific SMTPException
    mock_smtp.sendmail.side_effect = smtp_exception

    msg = EmailMessage()
    msg["Subject"] = "Hello"
    msg.set_content("Hi there")

    recipients = ["to@example.com"]

    # Act + Assert
    with pytest.raises(HTTPException) as ei:
        provider.send_mail(recipients, msg)

    # Validate error mapping and that quit was NOT called because exception branches before quit
    exc = ei.value
    assert exc.status_code == expected_code
    assert any(expected_detail in d for d in exc.detail)
    assert not mock_smtp.quit.called


def test_get_ticket_returns_none_when_add_ticket_empty(mocker):
    # Arrange
    provider = make_provider()
    provider.ADD_TICKET = ""
    imap_cls = mocker.patch("imaplib.IMAP4_SSL")

    # Act
    ticket = provider._get_ticket("user@example.com", 123)

    # Assert
    assert ticket is None
    imap_cls.assert_not_called()


def test_get_ticket_success(mocker):
    # Arrange
    provider = make_provider()
    provider.ADD_TICKET = "support@example.com"
    provider.TICKET_MATCH = r"\[Ticket#\d+\]"

    mock_imap = mocker.Mock()
    mocker.patch("imaplib.IMAP4_SSL", return_value=mock_imap)

    # Mock search result: one message UID
    mock_imap.uid.side_effect = [
        ("OK", [b"42"]),  # search
        ("OK", [[None, b"Subject: [Ticket#999]\r\n\r\nBody"]]),  # fetch
    ]

    # Act
    ticket = provider._get_ticket("user@example.com", 123)

    # Assert
    assert ticket == "[Ticket#999]"
    mock_imap.login.assert_called_once()
    mock_imap.select.assert_called_once_with("INBOX")
    mock_imap.logout.assert_called_once()


def test_get_ticket_no_match_returns_none(mocker):
    # Arrange
    provider = make_provider()
    provider.ADD_TICKET = "support@example.com"

    mock_imap = mocker.Mock()
    mocker.patch("imaplib.IMAP4_SSL", return_value=mock_imap)

    # Mock search result: no messages
    mock_imap.uid.return_value = ("OK", [b""])

    # Act
    ticket = provider._get_ticket("user@example.com", 123)

    # Assert
    assert ticket is None
    mock_imap.logout.assert_called_once()


def test_get_ticket_imap_error_logs_and_returns_none(mocker):
    # Arrange
    provider = make_provider()
    provider.ADD_TICKET = "support@example.com"

    mock_imap = mocker.Mock()
    mocker.patch("imaplib.IMAP4_SSL", return_value=mock_imap)
    mock_imap.login.side_effect = imaplib.IMAP4.error("Login failed")

    # Act
    ticket = provider._get_ticket("user@example.com", 123)

    # Assert
    assert ticket is None
    # Verify that it didn't crash and returned None as expected in except block


def test_get_ticket_imap_weirdness_logs_and_returns_none(mocker):
    # Arrange
    provider = make_provider()
    provider.ADD_TICKET = "support@example.com"

    mock_imap = mocker.Mock()
    mocker.patch("imaplib.IMAP4_SSL", return_value=mock_imap)
    mock_imap.login.side_effect = KeyError("Login failed")

    # Act
    ticket = provider._get_ticket("user@example.com", 123)

    # Assert
    assert ticket is None
    # Verify that it didn't crash and returned None as expected in except block
