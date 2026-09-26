# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
import pytest
from fastapi import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_422_UNPROCESSABLE_CONTENT

from providers.Google import ReCAPTCHAClient


@pytest.fixture
def client():
    return ReCAPTCHAClient(captcha_id="test_id", captcha_secret="test_secret")


@pytest.fixture
def mock_google(mocker):
    def _mock(status_code: int = 200, json_data: dict = None, text: str = ""):
        mock_rsp = mocker.MagicMock()
        mock_rsp.status_code = status_code
        if json_data is not None:
            mock_rsp.json.return_value = json_data
        mock_rsp.text = text
        return mocker.patch("requests.request", return_value=mock_rsp)

    return _mock


def test_validate_success(client, mock_google):
    mock_req = mock_google(status_code=200, json_data={"success": True})

    res = client.validate(remote_ip="192.168.1.1", response="valid_token")

    assert res is None
    mock_req.assert_called_once_with(
        "GET",
        url=ReCAPTCHAClient.API_ENDPOINT,
        params={
            "response": "valid_token",
            "secret": "test_secret",
            "remoteip": "192.168.1.1",
        },
    )


def test_validate_failure_google_error(client, mock_google):
    mock_google(
        status_code=200,
        json_data={"success": False, "error-codes": ["invalid-input-response"]},
        text='{"success": false, "error-codes": ["invalid-input-response"]}\n',
    )

    res = client.validate(remote_ip="192.168.1.1", response="invalid_token")

    assert res == '{"success": false, "error-codes": ["invalid-input-response"]}'


def test_validate_failure_http_error(client, mock_google):
    mock_google(
        status_code=500,
        json_data={"error": "Internal Server Error"},
        text="Internal Server Error\n",
    )

    res = client.validate(remote_ip="192.168.1.1", response="any_token")

    assert res == "Internal Server Error"


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


def test_verify_captcha_success(client, mock_google):
    mock_req = mock_google(status_code=200, json_data={"success": True})

    client.verify_captcha(["192.168.1.1", "valid_token"])
    mock_req.assert_called_once_with(
        "GET",
        url=ReCAPTCHAClient.API_ENDPOINT,
        params={
            "response": "valid_token",
            "secret": "test_secret",
            "remoteip": "192.168.1.1",
        },
    )


def test_verify_captcha_unauthorized(client, mock_google):
    mock_google(
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
