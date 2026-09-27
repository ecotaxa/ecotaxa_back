# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
import pytest
from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_422_UNPROCESSABLE_CONTENT

from helpers.AppConfig import Config
from providers.HomeCaptcha import HomeCaptcha


@pytest.fixture
def mock_request(mocker):
    def _mock(status_code: int = 200, json_data: dict = None, text: str = ""):
        mock_rsp = mocker.MagicMock()
        mock_rsp.status_code = status_code
        if json_data is not None:
            mock_rsp.json.return_value = json_data
        mock_rsp.text = text
        return mocker.patch("requests.request", return_value=mock_rsp)

    return _mock


def test_init_default(monkeypatch):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "")
    monkeypatch.setattr(Config, "get_all_in_one", lambda self: "off")
    monkeypatch.setattr(Config, "get_max_captcha_token_length", lambda self: 4096)

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    assert captcha.secret == "default_secret"
    assert captcha.recaptchaid == ""
    assert captcha.all_in_one is False
    assert captcha.max_token_length == 4096
    assert captcha._daily_get_iplist() is None


def test_init_with_recaptcha_secret(monkeypatch):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "google_id")
    monkeypatch.setattr(Config, "get_recaptchasecret", lambda self: "google_secret")

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    assert captcha.recaptchaid == "google_id"
    assert captcha.secret == "google_secret"


def test_init_with_recaptcha_id_only(monkeypatch):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "google_id")
    monkeypatch.setattr(Config, "get_recaptchasecret", lambda self: None)

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    assert captcha.recaptchaid == "google_id"
    assert captcha.secret == "default_secret"


def test_init_all_in_one(monkeypatch):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "")
    monkeypatch.setattr(Config, "get_all_in_one", lambda self: "on")

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    assert captcha.all_in_one is True


def test_validate_google_recaptcha_success(monkeypatch, mock_request):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "google_id")
    monkeypatch.setattr(Config, "get_recaptchasecret", lambda self: "google_secret")

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    mock_req = mock_request(status_code=200, json_data={"success": True})

    res = captcha.validate(remote_ip="192.168.1.1", response="valid_token")

    assert res is None
    mock_req.assert_called_once_with(
        "GET",
        url="https://www.google.com/recaptcha/api/siteverify",
        params={
            "response": "valid_token",
            "secret": "google_secret",
            "remoteip": "192.168.1.1",
        },
    )


def test_validate_google_recaptcha_failure_error(monkeypatch, mock_request):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "google_id")
    monkeypatch.setattr(Config, "get_recaptchasecret", lambda self: "google_secret")

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    mock_request(
        status_code=200,
        json_data={"success": False, "error-codes": ["invalid-input-response"]},
        text='{"success": false, "error-codes": ["invalid-input-response"]}\n',
    )

    res = captcha.validate(remote_ip="192.168.1.1", response="invalid_token")

    assert res == '{"success": false, "error-codes": ["invalid-input-response"]}'


def test_validate_google_recaptcha_http_error(monkeypatch, mock_request):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "google_id")
    monkeypatch.setattr(Config, "get_recaptchasecret", lambda self: "google_secret")

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    mock_request(
        status_code=500,
        json_data={"error": "Internal Server Error"},
        text="Internal Server Error\n",
    )

    res = captcha.validate(remote_ip="192.168.1.1", response="any_token")

    assert res == "Internal Server Error"


def test_validate_all_in_one(monkeypatch, mocker):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "")
    monkeypatch.setattr(Config, "get_all_in_one", lambda self: "on")

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    mock_req = mocker.patch("requests.request")

    res = captcha.validate(remote_ip="192.168.1.1", response="any_token")

    assert res is None
    mock_req.assert_not_called()


def test_validate_homecaptcha_gui_success(monkeypatch, mock_request):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "")
    monkeypatch.setattr(Config, "get_all_in_one", lambda self: "off")
    monkeypatch.setattr(
        Config, "get_account_validation_url", lambda self: "http://example.com/front/"
    )

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    mock_req = mock_request(status_code=200, json_data={"success": True})

    res = captcha.validate(remote_ip="192.168.1.1", response="valid_token")

    assert res is None
    mock_req.assert_called_once_with(
        "GET",
        url="http://example.com/front/gui/checkcaptcha",
        params={
            "r": "valid_token",
        },
    )


def test_validate_homecaptcha_gui_failure(monkeypatch, mock_request):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "")
    monkeypatch.setattr(Config, "get_all_in_one", lambda self: "off")
    monkeypatch.setattr(
        Config, "get_account_validation_url", lambda self: "http://example.com/front/"
    )

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    mock_request(
        status_code=200,
        json_data={"success": False},
        text='{"success": false}\n',
    )

    res = captcha.validate(remote_ip="192.168.1.1", response="invalid_token")

    assert res == '{"success": false}'


def test_validate_homecaptcha_gui_missing_success_field(monkeypatch, mock_request):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "")
    monkeypatch.setattr(Config, "get_all_in_one", lambda self: "off")
    monkeypatch.setattr(
        Config, "get_account_validation_url", lambda self: "http://example.com/front/"
    )

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    mock_request(
        status_code=200,
        json_data={"error": "unexpected format"},
        text='{"error": "unexpected format"}\n',
    )

    res = captcha.validate(remote_ip="192.168.1.1", response="invalid_token")

    assert res == '{"error": "unexpected format"}'


def test_validate_homecaptcha_gui_http_error(monkeypatch, mock_request):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "")
    monkeypatch.setattr(Config, "get_all_in_one", lambda self: "off")
    monkeypatch.setattr(
        Config, "get_account_validation_url", lambda self: "http://example.com/front/"
    )

    captcha = HomeCaptcha(homecaptcha_secret="default_secret")
    mock_request(
        status_code=502,
        json_data={"error": "Bad Gateway"},
        text="Bad Gateway\n",
    )

    res = captcha.validate(remote_ip="192.168.1.1", response="any_token")

    assert res == "Bad Gateway"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(Config, "get_recaptchaid", lambda self: "test_id")
    monkeypatch.setattr(Config, "get_recaptchasecret", lambda self: "test_secret")
    monkeypatch.setattr(Config, "get_max_captcha_token_length", lambda self: 4096)
    return HomeCaptcha(homecaptcha_secret="default_secret")


@pytest.mark.parametrize(
    "no_bot",
    [
        None,
        [],
        ["", ""],
    ],
)
def test_verify_captcha_needs_data(client, no_bot):
    with pytest.raises(HTTPException) as exc_info:
        client.verify_captcha(no_bot)

    assert exc_info.value.status_code == HTTP_422_UNPROCESSABLE_CONTENT
    assert exc_info.value.detail == ["reCaptcha verif needs data"]


@pytest.mark.parametrize(
    "no_bot",
    [
        ["only_one"],
        ["one", "two", "three"],
    ],
)
def test_verify_captcha_invalid_length(client, no_bot):
    with pytest.raises(HTTPException) as exc_info:
        client.verify_captcha(no_bot)

    assert exc_info.value.status_code == HTTP_422_UNPROCESSABLE_CONTENT
    assert exc_info.value.detail == ["invalid no_bot reason 1"]


@pytest.mark.parametrize(
    "no_bot",
    [
        ["x" * 4096, "token"],
        ["192.168.1.1", "x" * 4096],
        ["x" * 4096, "x" * 4096],
    ],
)
def test_verify_captcha_token_too_long(client, no_bot):
    with pytest.raises(HTTPException) as exc_info:
        client.verify_captcha(no_bot)

    assert exc_info.value.status_code == HTTP_422_UNPROCESSABLE_CONTENT
    assert exc_info.value.detail == ["invalid no_bot reason 2"]


def test_verify_captcha_success(client, mock_request):
    mock_req = mock_request(status_code=200, json_data={"success": True})

    client.verify_captcha(["192.168.1.1", "valid_token"])
    mock_req.assert_called_once_with(
        "GET",
        url="https://www.google.com/recaptcha/api/siteverify",
        params={
            "response": "valid_token",
            "secret": "test_secret",
            "remoteip": "192.168.1.1",
        },
    )


def test_verify_captcha_unauthorized(client, mock_request):
    mock_request(
        status_code=200,
        json_data={"success": False, "error-codes": ["invalid-input-response"]},
        text='{"success": false, "error-codes": ["invalid-input-response"]}\n',
    )

    with pytest.raises(HTTPException) as exc_info:
        client.verify_captcha(["192.168.1.1", "bad_token"])

    assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == [
        '{"success": false, "error-codes": ["invalid-input-response"]}'
    ]
