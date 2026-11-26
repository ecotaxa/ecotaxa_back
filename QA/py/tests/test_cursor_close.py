# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
from unittest.mock import MagicMock

import pytest

from BO.ProjectSet import FeatureConsistentProjectSet
from DB.Image import Image
from DB.Project import Project


class _DummyResult:
    def __init__(self, rows, *, fail_after_first: bool = False):
        self._rows = rows
        self._fail_after_first = fail_after_first
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.closed = True
        return False

    def __iter__(self):
        for idx, row in enumerate(self._rows):
            if self._fail_after_first and idx == 1:
                raise RuntimeError("mid-iteration failure")
            yield row

    def tuples(self):
        return iter(self)


def test_fetch_existing_images_closes_result_on_success_and_error():
    res_ok = _DummyResult([("obj1", "img1.jpg", 0)])
    session = MagicMock()
    session.execute.return_value = res_ok

    imgs, ranks = Image.fetch_existing_images(session, prj_id=1)
    assert res_ok.closed is True
    assert imgs == {"obj1*img1.jpg"}
    assert ranks.get("obj1") == 0

    res_err = _DummyResult(
        [("obj1", "img1.jpg", 0), ("obj2", "img2.jpg", 1)], fail_after_first=True
    )
    session.execute.return_value = res_err

    with pytest.raises(RuntimeError, match="mid-iteration failure"):
        Image.fetch_existing_images(session, prj_id=1)
    assert res_err.closed is True


def test_fetch_existing_ranks_closes_result_on_success_and_error():
    res_ok = _DummyResult([(100, 0)])
    session = MagicMock()
    session.execute.return_value = res_ok

    ranks = Project.fetch_existing_ranks(session, prj_id=1)
    assert res_ok.closed is True
    assert ranks.get(100) == 0

    res_err = _DummyResult([(100, 0), (101, 1)], fail_after_first=True)
    session.execute.return_value = res_err

    with pytest.raises(RuntimeError, match="mid-iteration failure"):
        Project.fetch_existing_ranks(session, prj_id=1)
    assert res_err.closed is True


def test_project_set_np_read_closes_result_on_early_stop_and_error():
    rows = [(1, 10, 1.5, 2.5), (2, 20, 3.5, 4.5), (3, 30, 5.5, 6.5)]

    # Early stop when nb_lines > 0
    res_limited = _DummyResult(rows)
    obj_ids = []
    classif_ids = []
    arr = FeatureConsistentProjectSet.np_read(
        res_limited, 2, ["c0", "c1"], obj_ids, classif_ids, {}
    )
    assert res_limited.closed is True
    assert obj_ids == [1, 2]
    assert classif_ids == [10, 20]
    assert arr.shape == (2, 2)

    # Full read when nb_lines == 0
    res_all = _DummyResult(rows)
    obj_ids_all = []
    classif_ids_all = []
    arr_all = FeatureConsistentProjectSet.np_read(
        res_all, 0, ["c0", "c1"], obj_ids_all, classif_ids_all, {}
    )
    assert res_all.closed is True
    assert obj_ids_all == [1, 2, 3]
    assert arr_all.shape == (3, 2)

    # Mid-iteration exception
    res_err = _DummyResult(rows, fail_after_first=True)
    with pytest.raises(RuntimeError, match="mid-iteration failure"):
        FeatureConsistentProjectSet.np_read(res_err, 0, ["c0", "c1"], [], [], {})
    assert res_err.closed is True


def test_project_set_np_read_all_closes_result_on_success_and_error():
    prj_set = FeatureConsistentProjectSet(
        session=MagicMock(), prj_ids=[1], column_names=["c0", "c1"]
    )
    res_ok = _DummyResult([(1, 10, 1.5, 2.5)])
    prj_set.read_all = MagicMock(return_value=res_ok)  # type: ignore[method-assign]
    arr, obj_ids, classif_ids = prj_set.np_read_all()
    assert res_ok.closed is True
    assert obj_ids == [1]
    assert classif_ids == [10]
    assert arr.shape == (1, 2)

    res_err = _DummyResult(
        [(1, 10, 1.5, 2.5), (2, 20, 3.5, 4.5)], fail_after_first=True
    )
    prj_set.read_all = MagicMock(return_value=res_err)  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="mid-iteration failure"):
        prj_set.np_read_all()
    assert res_err.closed is True
