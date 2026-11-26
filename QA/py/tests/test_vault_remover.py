import logging
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from API_operations.CRUD.Projects import ProjectsService
from API_operations.ObjectManager import ObjectManager
from API_operations.admin.ImageManager import ImageManagerService
from FS.VaultRemover import VaultRemover


class _DummyConfig:
    def __init__(self, vault_dir: str):
        self._vault_dir = vault_dir

    def vault_dir(self) -> str:
        return self._vault_dir


def _alive_vault_remover_threads():
    return [t for t in threading.enumerate() if t.name == "Vault remover" and t.is_alive()]


def test_vault_remover_is_daemon_and_stops_on_exception(tmp_path: Path):
    logger = logging.getLogger("test_vault_remover")
    cfg = _DummyConfig(str(tmp_path))

    with pytest.raises(RuntimeError, match="boom"):
        with VaultRemover(cfg, logger) as remover:  # type: ignore[arg-type]
            assert remover.daemon is True
            assert remover.is_alive()
            raise RuntimeError("boom")

    assert not remover.is_alive()
    assert _alive_vault_remover_threads() == []


def test_vault_remover_continues_on_image_path_and_oserror(tmp_path: Path, caplog):
    caplog.set_level(logging.ERROR)
    logger = logging.getLogger("test_vault_remover_errors")
    cfg = _DummyConfig(str(tmp_path))

    good1 = tmp_path / "good1.jpg"
    good2 = tmp_path / "good2.jpg"
    perm_err = tmp_path / "perm.jpg"
    good1.write_bytes(b"1")
    good2.write_bytes(b"2")
    perm_err.write_bytes(b"3")

    with patch("FS.VaultRemover.unlink") as mock_unlink:
        import os

        def flaky_unlink(path: str) -> None:
            if path.endswith("perm.jpg"):
                raise PermissionError("permission denied")
            if path.endswith("missing.jpg"):
                raise FileNotFoundError("not found")
            os.unlink(path)

        mock_unlink.side_effect = flaky_unlink

        with VaultRemover(cfg, logger) as remover:  # type: ignore[arg-type]
            orig_vault_image_path = remover.vault.image_path

            def flaky_image_path(sub_path: str) -> str:
                if sub_path == "bad_path.jpg":
                    raise ValueError("invalid path")
                return orig_vault_image_path(sub_path)

            remover.vault.image_path = flaky_image_path  # type: ignore[method-assign]
            remover.add_files(
                ["good1.jpg", "bad_path.jpg", "missing.jpg", "perm.jpg", "good2.jpg"]
            )

    assert not remover.is_alive()
    assert not good1.exists()
    assert not good2.exists()
    assert any("Could not remove file bad_path.jpg" in m for m in caplog.messages)
    assert any("Could not remove file perm.jpg" in m for m in caplog.messages)
    assert any("Could not remove file(s) missing.jpg" in m for m in caplog.messages)


def test_projects_delete_no_thread_leak_on_exception(fastapi, monkeypatch):
    from tests.credentials import ADMIN_USER_ID
    from tests.test_import_simple import do_simple_import_images

    prj_id = do_simple_import_images(fastapi, title="Project delete leak test")

    with ProjectsService() as sce:
        monkeypatch.setattr(
            sce.session,
            "commit",
            lambda: (_ for _ in ()).throw(RuntimeError("commit failed")),
        )
        with pytest.raises(RuntimeError, match="commit failed"):
            sce.delete(ADMIN_USER_ID, prj_id, only_objects=False)

    assert _alive_vault_remover_threads() == []


def test_object_manager_delete_no_thread_leak_on_exception(fastapi, monkeypatch):
    from BO.ObjectSet import EnumeratedObjectSet
    from DB.Acquisition import Acquisition
    from DB.Object import ObjectHeader
    from DB.Sample import Sample
    from tests.credentials import ADMIN_USER_ID
    from tests.test_import import do_import_uvp6

    prj_id, _ = do_import_uvp6(fastapi, "Object delete leak test")
    with ObjectManager() as sce:
        obj_ids = [
            row[0]
            for row in sce.session.query(ObjectHeader.objid)
            .join(Acquisition, Acquisition.acquisid == ObjectHeader.acquisid)
            .join(Sample, Sample.sampleid == Acquisition.acq_sample_id)
            .filter(Sample.projid == prj_id)
            .all()
        ]
        assert len(obj_ids) > 0

        monkeypatch.setattr(
            EnumeratedObjectSet,
            "delete",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("delete failed")),
        )
        with pytest.raises(RuntimeError, match="delete failed"):
            sce.delete(ADMIN_USER_ID, obj_ids[:1])

    assert _alive_vault_remover_threads() == []


def test_image_manager_cleanup_no_thread_leak_on_exception(fastapi, monkeypatch):
    from tests.credentials import ADMIN_USER_ID
    from tests.test_admin_images import PROJECT_DIGEST_URL, duplicate_images_for_object
    from tests.test_import import do_import_uvp6

    prj_id, _ = do_import_uvp6(fastapi, "Test ImageManager Leak")
    duplicate_images_for_object(prj_id, count=1)
    from tests.credentials import ADMIN_AUTH

    rsp = fastapi.get(PROJECT_DIGEST_URL.format(project_id=prj_id), headers=ADMIN_AUTH)
    assert rsp.status_code == 200

    with ImageManagerService() as sce:
        monkeypatch.setattr(
            sce.vault,
            "image_path",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("vault failed")),
        )
        with pytest.raises(RuntimeError, match="vault failed"):
            sce.do_cleanup_dup_same_obj(ADMIN_USER_ID, prj_id, max_deletes=10)

    assert _alive_vault_remover_threads() == []
