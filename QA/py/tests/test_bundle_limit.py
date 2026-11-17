#
# InBundle MAX_FILES limit: a UVP6 sample counts for 1, be it an *Images.zip
# or an *Images directory (e.g. after recursive unzip on upload).
#
import zipfile
from pathlib import Path

import pytest

from BO.Bundle import InBundle


def _uvp6_dir(base: Path, sample: str) -> None:
    sample_dir = base / (sample + "_Images")
    sample_dir.mkdir()
    (sample_dir / ("ecotaxa_" + sample + ".tsv")).write_text("object_id\n[t]\n")


def _uvp6_zip(base: Path, sample: str) -> None:
    with zipfile.ZipFile(base / (sample + "_Images.zip"), "w") as z:
        z.writestr("ecotaxa_" + sample + ".tsv", "object_id\n[t]\n")


@pytest.mark.parametrize("maker", [_uvp6_dir, _uvp6_zip])
def test_uvp6_samples_count_once(tmp_path, monkeypatch, maker):
    monkeypatch.setattr(InBundle, "MAX_FILES", 3)
    src = tmp_path / "src"
    src.mkdir()
    temp = tmp_path / "temp"
    temp.mkdir()
    for i in range(3):
        maker(src, "s%d" % i)
    # 3 samples, limit 3: OK (dirs used to count 6)
    bundle = InBundle(src.as_posix(), "[base]", temp)
    assert len(bundle.sub_bundles) == 3
    assert bundle.possible_files == []
    # One more: over the limit
    maker(src, "s3")
    with pytest.raises(ImportError, match="too many files"):
        InBundle(src.as_posix(), "[base]", temp)


def test_plain_tsvs_and_uvp6_mixed(tmp_path, monkeypatch):
    monkeypatch.setattr(InBundle, "MAX_FILES", 3)
    src = tmp_path / "src"
    src.mkdir()
    temp = tmp_path / "temp"
    temp.mkdir()
    (src / "ecotaxa_a.tsv").write_text("object_id\n[t]\n")
    _uvp6_dir(src, "s0")
    _uvp6_zip(src, "s1")
    InBundle(src.as_posix(), "[base]", temp)
    (src / "ecotaxa_b.tsv").write_text("object_id\n[t]\n")
    with pytest.raises(ImportError, match="too many files"):
        InBundle(src.as_posix(), "[base]", temp)
