# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Some functions around filesystem<->DB consistency in vault directory
#
import filecmp
import hashlib
from os.path import exists
from typing import Optional, Set

from sqlalchemy import and_

from API_operations.helpers.Service import Service
from BO.Rights import RightsBO
from BO.User import UserIDT
from DB.Acquisition import Acquisition
from DB.Image import Image, ImageFile, ImageFileStateEnum
from DB.Object import ObjectHeader
from DB.Project import ProjectIDT, Project
from DB.Sample import Sample
from DB.User import Role
from DB.helpers.ORM import aliased
from FS.Vault import Vault
from FS.VaultRemover import VaultRemover
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

logger = get_logger(__name__)


class ImageManagerService(Service):
    def __init__(self) -> None:
        super().__init__()
        self.vault = Vault(self.config.vault_dir())

    @staticmethod
    def compute_md5(fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.digest()

    def do_digests(
        self, current_user_id: UserIDT, prj_id: Optional[ProjectIDT], max_digests: int
    ) -> str:
        """
        Pick some images without checksum and compute it.
        """
        _user = RightsBO.user_has_role(
            self.ro_session, current_user_id, Role.APP_ADMINISTRATOR
        )
        qry = self.ro_session.query(Image.file_name)
        if prj_id is not None:
            # Find missing images in a project
            qry = qry.join(ObjectHeader).join(Acquisition).join(Sample).join(Project)
            qry = qry.filter(Project.projid == prj_id)
        else:
            # Find missing images globally
            pass
        qry = qry.outerjoin(ImageFile, Image.file_name == ImageFile.path)
        qry = qry.filter(ImageFile.path.is_(None))
        qry = qry.limit(max_digests)
        cnt = 0
        with CodeTimer("Files without md5, query '%s':" % str(qry), logger):
            files_without_md5 = [file_name for file_name, in qry]
        for an_img_file_name in files_without_md5:
            cnt += 1
            img_file = ImageFile(path=an_img_file_name)
            self.session.add(img_file)
            self._md5_on_record(img_file)
            if cnt % 100 == 0:
                self.session.commit()
        self.session.commit()
        # Eventually we can still satisfy the constraint while doing a few missing md5s
        left_for_unknown = max_digests - cnt
        if left_for_unknown > 0:
            # Also do unknown image file lines
            miss_qry = self.session.query(ImageFile)
            miss_qry = miss_qry.filter(
                and_(
                    ImageFile.state == ImageFileStateEnum.UNKNOWN.value,
                    ImageFile.digest_type == "?",
                )
            )
            if prj_id is not None:
                # Find unknown images in a project
                miss_qry = miss_qry.outerjoin(Image, Image.file_name == ImageFile.path)
                miss_qry = (
                    miss_qry.join(ObjectHeader)
                    .join(Acquisition)
                    .join(Sample)
                    .join(Project)
                )
                miss_qry = miss_qry.filter(Project.projid == prj_id)
            # On purpose, no "order by" clause. Results are random, but sorting takes a while on lots of images
            miss_qry = miss_qry.limit(left_for_unknown)
            with CodeTimer(
                "Files with unknown state, query '%s':" % str(miss_qry), logger
            ):
                missing_ones = [an_img_file for an_img_file in miss_qry]
            for a_missing in missing_ones:
                cnt += 1
                self._md5_on_record(a_missing)
            self.session.commit()
        return "Digest for %d images done." % cnt

    def _md5_on_record(self, img_file: ImageFile):
        img_file_path = self.vault.image_path(img_file.path)
        try:
            md5 = self.compute_md5(img_file_path)
            img_file.digest = md5
            img_file.digest_type = "5"
            img_file.state = ImageFileStateEnum.OK.value
        except FileNotFoundError:
            img_file.state = ImageFileStateEnum.MISSING.value
        except Exception as e:
            logger.exception(e)
            img_file.state = ImageFileStateEnum.ERROR.value

    def do_cleanup_dup_same_obj(
        self, current_user_id: UserIDT, prj_id: ProjectIDT, max_deletes: int
    ) -> str:
        """
        Simplest duplication pattern. Inside the same object there are several identical images.
        """
        _user = RightsBO.user_has_role(
            self.ro_session, current_user_id, Role.APP_ADMINISTRATOR
        )
        orig_img = aliased(Image, name="orig")
        orig_file = aliased(ImageFile, name="orig_file")
        qry = self.session.query(
            orig_img.file_name, orig_img.imgid, Image, ImageFile
        )  # Select what to delete
        qry = (
            qry.join(ObjectHeader, ObjectHeader.objid == Image.objid)
            .join(Acquisition)
            .join(Sample)
            .join(Project)
        )
        # We consider that original image is the oldest one, so others have a superior ID
        qry = qry.join(
            orig_img,
            and_(
                orig_img.objid == Image.objid,
                orig_img.orig_file_name == Image.orig_file_name,
                orig_img.width == Image.width,
                orig_img.height == Image.height,
                orig_img.imgid < Image.imgid,
            ),
        )
        # Must have a checksum, with the same state (sane)
        qry = qry.join(
            ImageFile,
            and_(
                ImageFile.path == Image.file_name,
                ImageFile.state == ImageFileStateEnum.OK.value,
            ),
        )
        qry = qry.join(
            orig_file,
            and_(
                orig_file.path == orig_img.file_name,
                orig_file.state == ImageFileStateEnum.OK.value,
            ),
        )
        # and the same value of course
        qry = qry.filter(
            and_(
                ImageFile.digest_type == orig_file.digest_type,
                ImageFile.digest == orig_file.digest,
            )
        )
        qry = qry.filter(Project.projid == prj_id)
        qry = qry.order_by(Image.objid, orig_img.imgid, Image.imgid)
        qry = qry.limit(max_deletes)
        with CodeTimer(
            "Dups same objs inside %d, query '%s':" % (prj_id, str(qry)), logger
        ):
            to_do = [
                (orig_file_name, orig_img_id, an_image, an_image_file)
                for orig_file_name, orig_img_id, an_image, an_image_file in qry
            ]
        ko_not_same = 0
        ko_except = 0
        # Prepare & start a remover thread that will run in // with DB queries
        remover = VaultRemover(self.config, logger).do_start()
        filecmp.clear_cache()
        deleted_imgids: Set[int] = set()
        for orig_file_name, orig_img_id, an_image, an_image_file in to_do:
            # The query returns multiple rows if there are more than 2 duplicates
            if orig_img_id in deleted_imgids:
                continue
            # Even if MD5s match, be paranoid and compare files
            orig_path = self.vault.image_path(orig_file_name)
            dup_path = self.vault.image_path(an_image.file_name)
            assert orig_path != dup_path
            orig_exists = exists(orig_path)
            dup_exists = exists(dup_path)
            if orig_exists:
                if dup_exists:
                    try:
                        same = filecmp.cmp(orig_path, dup_path, False)
                    except Exception as exc:
                        logger.info(
                            "Exception while comparing orig:%s and dup:%s: %s",
                            orig_path,
                            dup_path,
                            str(exc),
                        )
                        ko_except += 1
                        continue
                    if not same:
                        ko_not_same += 1
                        continue
                else:
                    # Duplicate is gone already
                    pass
            else:
                # DB record of physical file is wrong
                # TODO
                continue
            # Do the cleanup
            deleted_imgids.add(an_image.imgid)
            if dup_exists:
                remover.add_files([an_image.file_name])
            self.session.delete(an_image)
            self.session.delete(an_image_file)
        # Wait for the files handled
        self.session.commit()
        remover.wait_for_done()
        return (
            "Dupl remover for %s dup images done but %d problems %d false file comp"
            % (len(deleted_imgids), ko_except, ko_not_same)
        )
