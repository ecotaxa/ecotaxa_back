# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from FS.Vault import Vault


def _make_mock_response(status_code: int, chunks=None, iter_exc=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    if iter_exc is not None:

        def _failing_iter(_chunk_size):
            yield b"partial"
            raise iter_exc

        resp.iter_content.side_effect = _failing_iter
    else:
        resp.iter_content.return_value = iter(chunks or [])
    return resp


def test_ensure_there_closes_response_and_sets_timeout_on_non_200(tmp_path):
    vault = Vault(str(tmp_path))
    target = tmp_path / "0000" / "0001.jpg"
    mock_resp = _make_mock_response(404)

    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = vault.ensure_there(target, "0000/0001.jpg")

    assert res is False
    assert not target.exists()
    assert mock_get.call_args.kwargs.get("timeout") is not None
    assert mock_resp.__exit__.called or mock_resp.close.called


def test_ensure_there_cleans_temp_file_and_closes_response_on_iter_error(tmp_path):
    vault = Vault(str(tmp_path))
    target = tmp_path / "0000" / "0002.jpg"
    mock_resp = _make_mock_response(200, iter_exc=RuntimeError("stream broken"))

    created_tmp_files = []
    orig_named_tmp = __import__("tempfile").NamedTemporaryFile
    orig_mktemp = __import__("tempfile").mktemp

    def _track_named_tmp(*args, **kwargs):
        f = orig_named_tmp(*args, **kwargs)
        created_tmp_files.append(Path(f.name))
        return f

    def _track_mktemp(*args, **kwargs):
        p = orig_mktemp(*args, **kwargs)
        created_tmp_files.append(Path(p))
        return p

    with (
        patch("requests.get", return_value=mock_resp) as mock_get,
        patch("tempfile.NamedTemporaryFile", side_effect=_track_named_tmp),
        patch("tempfile.mktemp", side_effect=_track_mktemp),
    ):
        with pytest.raises(RuntimeError, match="stream broken"):
            vault.ensure_there(target, "0000/0002.jpg")

    assert mock_get.call_args.kwargs.get("timeout") is not None
    assert mock_resp.__exit__.called or mock_resp.close.called
    assert len(created_tmp_files) == 1
    assert not created_tmp_files[0].exists()


def test_ensure_there_downloads_stores_and_cleans_up(tmp_path):
    vault = Vault(str(tmp_path))
    target = tmp_path / "0000" / "0003_mini.jpg"
    mock_resp = _make_mock_response(200, chunks=[b"abc", b"def"])

    created_tmp_files = []
    orig_named_tmp = __import__("tempfile").NamedTemporaryFile

    def _track_named_tmp(*args, **kwargs):
        f = orig_named_tmp(*args, **kwargs)
        created_tmp_files.append(Path(f.name))
        return f

    with (
        patch("requests.get", return_value=mock_resp) as mock_get,
        patch("tempfile.NamedTemporaryFile", side_effect=_track_named_tmp),
    ):
        res = vault.ensure_there(target, "0000/0003_mini.jpg")

    assert res is False
    assert mock_get.call_args.kwargs.get("timeout") is not None
    assert mock_resp.__exit__.called or mock_resp.close.called
    assert target.exists()
    assert target.read_bytes() == b"abcdef"
    assert len(created_tmp_files) == 1
    assert not created_tmp_files[0].exists()


def test_ensure_there_cleans_temp_file_on_store_error(tmp_path):
    vault = Vault(str(tmp_path))
    target = tmp_path / "0000" / "0004.jpg"
    mock_resp = _make_mock_response(200, chunks=[b"abc"])

    created_tmp_files = []
    orig_named_tmp = __import__("tempfile").NamedTemporaryFile

    def _track_named_tmp(*args, **kwargs):
        f = orig_named_tmp(*args, **kwargs)
        created_tmp_files.append(Path(f.name))
        return f

    with (
        patch("requests.get", return_value=mock_resp),
        patch("tempfile.NamedTemporaryFile", side_effect=_track_named_tmp),
        patch.object(vault, "store_image", side_effect=OSError("disk full")),
    ):
        with pytest.raises(OSError, match="disk full"):
            vault.ensure_there(target, "0000/0004.jpg")

    assert mock_resp.__exit__.called or mock_resp.close.called
    assert len(created_tmp_files) == 1
    assert not created_tmp_files[0].exists()
