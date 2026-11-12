#
# My Files unpacking: resulting layout on success.
# These freeze the layout produced before extraction was staged, it must not change.
#
from pathlib import Path

from tests.userfiles_helpers import make_user_dir, zip_bytes, tree, TSV, PNG_1X1


def _setup(tmp_path: Path):
    root = tmp_path / "user"
    parent = root / "up"
    parent.mkdir(parents=True)
    return root, parent


def _upload(parent: Path, name: str, content: bytes) -> Path:
    archive = parent / name
    archive.write_bytes(content)
    return archive


def test_zip_root_members(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, "img/x.png": PNG_1X1})
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv", "name/img/", "name/img/x.png"]


def test_zip_already_wrapped(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent, "name.zip", zip_bytes({"name/a.tsv": TSV, "name/x.png": PNG_1X1})
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv", "name/x.png"]


def test_zip_nested(tmp_path):
    root, parent = _setup(tmp_path)
    inner = zip_bytes({"ecotaxa_inner.tsv": TSV, "x.png": PNG_1X1})
    archive = _upload(
        parent,
        "name.zip",
        zip_bytes({"a.tsv": TSV, "sub/inner_Images.zip": inner, "top.zip": inner}),
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == [
        "name/",
        "name/a.tsv",
        "name/sub/",
        "name/sub/inner_Images/",
        "name/sub/inner_Images/ecotaxa_inner.tsv",
        "name/sub/inner_Images/x.png",
        "name/top/",
        "name/top/ecotaxa_inner.tsv",
        "name/top/x.png",
    ]


def test_zip_unaccepted_member_removed(tmp_path):
    root, parent = _setup(tmp_path)
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, "evil.bin": b"\x7fELF\x02\x01"})
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == ["name/", "name/a.tsv"]


def test_zip_onto_existing_folder(tmp_path):
    root, parent = _setup(tmp_path)
    (parent / "name").mkdir()
    (parent / "name" / "old.tsv").write_bytes(TSV)
    (parent / "name" / "a.tsv").write_bytes(b"replaced\n")
    archive = _upload(
        parent, "name.zip", zip_bytes({"a.tsv": TSV, "img/x.png": PNG_1X1})
    )
    make_user_dir(root).dispatch_unpack(archive, parent)
    assert tree(parent) == [
        "name/",
        "name/a.tsv",
        "name/img/",
        "name/img/x.png",
        "name/old.tsv",
    ]
    assert (parent / "name" / "a.tsv").read_bytes() == TSV
