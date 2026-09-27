from pathlib import Path
from typing import NamedTuple

from starlette import status

from API_operations.helpers.Service import Service
from DB.Acquisition import Acquisition
from DB.Image import Image
from DB.Object import ObjectHeader
from DB.Sample import Sample
from FS.Vault import Vault
from tests.credentials import ADMIN_AUTH, USER_AUTH
from tests.test_import import do_import_uvp6

PROJECT_DIGEST_URL = "/admin/images/{project_id}/digest?max_digests=100"
CLEANUP_URL = "/admin/images/cleanup1?project_id={project_id}"


class DuplicateImagesInfo(NamedTuple):
    obj_id: int
    orig_img_id: int
    orig_img_file: str
    initial_img_count: int
    dup_ids: list[int]
    dup_files: list[str]


def duplicate_images_for_object(prj_id: int, count: int = 2) -> DuplicateImagesInfo:
    """
    Finds the first image in the given project and creates identical duplicates
    for the same object in the database and Vault.
    """
    with Service() as sce:
        vault = Vault(sce.config.vault_dir())
        first_img = (
            sce.session.query(Image)
            .join(ObjectHeader, ObjectHeader.objid == Image.objid)
            .join(Acquisition, Acquisition.acquisid == ObjectHeader.acquisid)
            .join(Sample, Sample.sampleid == Acquisition.acq_sample_id)
            .filter(Sample.projid == prj_id)
            .order_by(Image.objid, Image.imgrank)
            .first()
        )
        assert first_img is not None
        obj_id = first_img.objid
        orig_img_id = first_img.imgid
        orig_img_file = first_img.img_to_file()
        orig_vault_path = Path(vault.image_path(orig_img_file))
        assert orig_vault_path.exists()

        initial_obj_images = (
            sce.session.query(Image).filter(Image.objid == obj_id).all()
        )
        initial_img_count = len(initial_obj_images)
        max_rank = max(img.imgrank for img in initial_obj_images)

        dup_ids: list[int] = []
        dup_files: list[str] = []
        for i in range(1, count + 1):
            dup = Image(
                objid=obj_id,
                imgrank=max_rank + i,
                width=first_img.width,
                height=first_img.height,
                orig_file_name=first_img.orig_file_name,
                thumb_width=first_img.thumb_width,
                thumb_height=first_img.thumb_height,
            )
            sce.session.add(dup)
            sce.session.commit()
            vault.store_image(orig_vault_path, dup.imgid)
            dup_ids.append(dup.imgid)
            dup_file = dup.img_to_file()
            dup_files.append(dup_file)
            dup_path = Path(vault.image_path(dup_file))
            assert dup_path.exists()

        return DuplicateImagesInfo(
            obj_id=obj_id,
            orig_img_id=orig_img_id,
            orig_img_file=orig_img_file,
            initial_img_count=initial_img_count,
            dup_ids=dup_ids,
            dup_files=dup_files,
        )


def test_admin_images_digest(fastapi):

    prj_id, _ = do_import_uvp6(fastapi, "Test Project Admin")

    url = PROJECT_DIGEST_URL.format(project_id=prj_id)

    # Simple user cannot
    rsp = fastapi.get(url, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Admin can
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == "Digest for 30 images done."

    # TODO: some common error cases

    # md5 is persisted
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert rsp.json() == "Digest for 0 images done."


def test_admin_images_cleanup(fastapi):
    # Prepare a project with some images
    prj_id, _ = do_import_uvp6(fastapi, "Test Project Admin Images Cleanup1")

    # Prepare several identical images for an object
    dup_info = duplicate_images_for_object(prj_id, count=2)

    url = PROJECT_DIGEST_URL.format(project_id=prj_id)
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert isinstance(rsp.json(), str)
    assert rsp.json() == "Digest for 32 images done."

    url = CLEANUP_URL.format(project_id=prj_id)

    # Simple user cannot access the admin cleanup endpoint
    rsp = fastapi.get(url, headers=USER_AUTH)
    assert rsp.status_code == status.HTTP_403_FORBIDDEN

    # Admin can
    rsp = fastapi.get(url, headers=ADMIN_AUTH)
    assert rsp.status_code == status.HTTP_200_OK
    assert isinstance(rsp.json(), str)
    assert (
        rsp.json()
        == "Dupl remover for 2 dup images done but 0 problems 0 false file comp"
    )

    # Verify duplicate images and physical files were removed
    with Service() as sce:
        vault = Vault(sce.config.vault_dir())
        images_left = (
            sce.session.query(Image).filter(Image.objid == dup_info.obj_id).all()
        )
        assert len(images_left) == dup_info.initial_img_count
        images_left_ids = [img.imgid for img in images_left]
        assert dup_info.orig_img_id in images_left_ids
        for dup_id in dup_info.dup_ids:
            assert dup_id not in images_left_ids
        assert Path(vault.image_path(dup_info.orig_img_file)).exists()
        for dup_file in dup_info.dup_files:
            assert not Path(vault.image_path(dup_file)).exists()
