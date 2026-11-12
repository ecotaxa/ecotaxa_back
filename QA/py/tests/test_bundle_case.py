#
# InBundle finds import files whatever the case of their names.
#
import zipfile
from pathlib import Path

from BO.Bundle import InBundle

TSV = "object_id\n[t]\nobj1\n"


def _bundle(src: Path, tmp_path: Path) -> InBundle:
    temp = tmp_path / "temp"
    temp.mkdir(exist_ok=True)
    return InBundle(src.as_posix(), "[base]", temp)


def test_tsv_any_case(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    for a_name in ("ecotaxa_a.TSV", "Ecotaxa_b.tsv", "ecotaxa_c.Txt", "other.tsv"):
        (src / a_name).write_text(TSV)
    bundle = _bundle(src, tmp_path)
    assert sorted(bundle.possible_files_as_posix()) == [
        "Ecotaxa_b.tsv",
        "ecotaxa_a.TSV",
        "ecotaxa_c.Txt",
    ]


def test_uvp6_dir_and_zip_any_case(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    # UVP6 directory, with its TSV in upper case
    a_dir = src / "s1_IMAGES"
    a_dir.mkdir()
    (a_dir / "ECOTAXA_s1.TSV").write_text(TSV)
    # UVP6 zip, in upper case
    with zipfile.ZipFile(src / "s2_Images.ZIP", "w") as z:
        z.writestr("ecotaxa_s2.tsv", TSV)
    bundle = _bundle(src, tmp_path)
    # Both are UVP6 sub-bundles, the directory's TSV is not a plain import file
    assert list(bundle.possible_files_as_posix()) == []
    assert sorted(a_sub.path.name for a_sub in bundle.sub_bundles) == [
        "s1_IMAGES",
        "s2_Images",
    ]
    assert [list(a_sub.possible_files_as_posix()) for a_sub in bundle.sub_bundles]


def test_images_any_case(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    for a_name in ("a.JPG", "b.Png", "c.tif", "d.gif"):
        (src / a_name).write_bytes(b"x")
    bundle = _bundle(src, tmp_path)
    assert sorted(p.as_posix() for p in bundle.list_image_files()) == [
        "a.JPG",
        "b.Png",
        "c.tif",
    ]
