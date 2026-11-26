# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import builtins
import csv
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PIL import Image as PIL_Image

from BO.Mappings import ProjectMapping
from BO.TSVFile import TSVFile


@pytest.mark.parametrize(
    "raw_bytes,expected_fields,expected_types",
    [
        (
            b"object_id\tobject_lat\n[t]\t[f]\nobj1\t1.5\n",
            ["object_id", "object_lat"],
            {"object_id": "[t]", "object_lat": "[f]"},
        ),
        (
            b"\xef\xbb\xbfobject_id\tobject_lat\n[t]\t[f]\nobj1\t1.5\n",
            ["object_id", "object_lat"],
            {"object_id": "[t]", "object_lat": "[f]"},
        ),
        (
            b"object_id\tobject_lat\n",
            ["object_id", "object_lat"],
            {},
        ),
    ],
)
def test_tsv_open_closes_fd_and_clears_rdr(
    tmp_path: Path, raw_bytes: bytes, expected_fields: list, expected_types: dict
):
    tsv_path = tmp_path / "test.tsv"
    tsv_path.write_bytes(raw_bytes)
    tsv = TSVFile(tsv_path, "test.tsv", tmp_path)

    with tsv.open() as csv_file:
        assert not csv_file.closed
        assert hasattr(tsv, "rdr")
        assert list(tsv.clean_fields.values()) == expected_fields
        assert tsv.type_line == expected_types

    assert csv_file.closed
    assert not hasattr(tsv, "rdr")


@pytest.mark.parametrize(
    "raw_bytes,exc_type,use_small_field_limit",
    [
        # UTF-8 BOM triggers utf-8-sig reopen, followed by invalid UTF-8 bytes
        (b"\xef\xbb\xbf\xff\xfe\n", UnicodeDecodeError, False),
        # Field exceeding csv.field_size_limit triggers csv.Error when reading header
        (b"object_id\tobject_lat\n[t]\t[f]\n", csv.Error, True),
    ],
)
def test_tsv_open_closes_fd_on_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_bytes: bytes,
    exc_type: type,
    use_small_field_limit: bool,
):
    tsv_path = tmp_path / "bad.tsv"
    tsv_path.write_bytes(raw_bytes)
    tsv = TSVFile(tsv_path, "bad.tsv", tmp_path)

    opened_files = []
    real_open = builtins.open

    def tracking_open(*args, **kwargs):
        f = real_open(*args, **kwargs)
        opened_files.append(f)
        return f

    monkeypatch.setattr(builtins, "open", tracking_open)

    old_limit = csv.field_size_limit()
    if use_small_field_limit:
        csv.field_size_limit(5)
    try:
        with pytest.raises(exc_type):
            with tsv.open():
                pass
    finally:
        csv.field_size_limit(old_limit)

    assert len(opened_files) >= 1
    assert all(f.closed for f in opened_files)
    assert not hasattr(tsv, "rdr")


def test_tsv_do_import_closes_backup_pil_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    img_path = tmp_path / "img.png"
    PIL_Image.new("RGB", (12, 24)).save(img_path)

    tsv_path = tmp_path / "ecotaxa_test.tsv"
    tsv_path.write_text(
        "object_id\timg_file_name\n[t]\t[t]\nobj1\timg.png\n",
        encoding="utf-8",
    )

    tsv = TSVFile(tsv_path, "ecotaxa_test.tsv", tmp_path)

    opened_images = []
    real_pil_open = PIL_Image.open

    def tracking_pil_open(*args, **kwargs):
        im = real_pil_open(*args, **kwargs)
        opened_images.append(im)
        return im

    monkeypatch.setattr("BO.TSVFile.PIL_Image.open", tracking_pil_open)
    monkeypatch.setattr(tsv, "create_or_link_slaves", lambda *args, **kwargs: 2)
    monkeypatch.setattr(tsv, "deal_with_images", lambda *args, **kwargs: None)
    monkeypatch.setattr(tsv, "add_parent_objects", lambda *args, **kwargs: None)

    db_writer = MagicMock()
    db_writer.session = MagicMock()

    def set_objid(obj_head, *_args):
        obj_head.objid = 100

    def set_backup_imgid(_obj, backup_img):
        backup_img.imgid = 42

    db_writer.add_db_entities.side_effect = set_objid
    db_writer.add_vignette_backup.side_effect = set_backup_imgid

    vault = MagicMock()
    vault.store_image.return_value = "sub/img.png"
    vault.image_path.return_value = img_path

    vignette_maker = MagicMock()
    vignette_maker.make_vignette.return_value = img_path
    vignette_maker.must_keep_original.return_value = True

    where = SimpleNamespace(db_writer=db_writer, vault=vault)
    how = SimpleNamespace(
        user_id=1,
        prj_id=1,
        custom_mapping=ProjectMapping(),
        can_update_only=False,
        objects_and_images_to_skip=set(),
        existing_objects={},
        vignette_maker=vignette_maker,
    )
    stats = SimpleNamespace(
        current_row_count=0,
        start_time=datetime.now(),
        report=lambda _c: None,
    )

    rows = tsv.do_import(where, how, stats)  # type: ignore[arg-type]
    assert rows == 1
    assert len(opened_images) == 1
    assert opened_images[0].fp is None
