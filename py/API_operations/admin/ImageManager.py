# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Some functions around filesystem<->DB consistency in vault directory
#
import filecmp
import hashlib
from os.path import join
from typing import Optional, Set

from sqlalchemy import func, and_
from sqlalchemy.orm import aliased

from API_operations.helpers.Service import Service
from BO.Project import ProjectIDT
from BO.Rights import RightsBO
from BO.User import UserIDT
from DB import ObjectHeader, Sample, Acquisition, Project, Role
from DB.Image import Image, ImageFile, ImageFileStateEnum
from DB.helpers.ORM import Query
from FS.Vault import Vault
from FS.VaultRemover import VaultRemover
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

logger = get_logger(__name__)


class ImageManagerService(Service):

    def __init__(self):
        super().__init__()
        self.vault = Vault(join(self.link_src, 'vault'))

    @staticmethod
    def compute_md5(fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.digest()

    def do_digests(self, current_user_id: UserIDT,
                   prj_id: Optional[ProjectIDT],
                   max_digests: int) -> str:
        """
            Pick some images without checksum and compute it.
        """
        _user = RightsBO.user_has_role(self.session, current_user_id, Role.APP_ADMINISTRATOR)
        qry: Query = self.session.query(Image.file_name)
        if prj_id is not None:
            # Find missing images in a project
            qry = qry.join(ObjectHeader).join(Acquisition).join(Sample).join(Project)
            qry = qry.outerjoin(ImageFile, Image.file_name == ImageFile.path)
            qry = qry.filter(ImageFile.path.is_(None))
            qry = qry.filter(Project.projid == prj_id)
        else:
            # Find images newer than the newest known one
            sub_qry = self.session.query(func.max(ImageFile.path))
            qry = qry.filter(Image.file_name > sub_qry)
        qry = qry.limit(max_digests)
        cnt = 0
        with CodeTimer("Files without md5, query '%s':" % str(qry), logger):
            files_without_md5 = [file_name for file_name, in qry.all()]
        for an_img_file_name in files_without_md5:
            cnt += 1
            img_file = ImageFile(path=an_img_file_name)
            self.session.add(img_file)
            img_file_path = self.vault.sub_path(an_img_file_name)
            try:
                md5 = self.compute_md5(img_file_path)
                img_file.digest = md5
                img_file.digest_type = '5'
                img_file.state = ImageFileStateEnum.OK.value
            except FileNotFoundError:
                img_file.state = ImageFileStateEnum.MISSING.value
            except Exception as e:
                logger.exception(e)
                img_file.state = ImageFileStateEnum.ERROR.value
        self.session.commit()
        return "Digest for %d images done." % cnt

    def do_cleanup_dup_same_obj(self, current_user_id: UserIDT,
                                prj_id: ProjectIDT,
                                max_deletes: int) -> str:
        """
            Simplest duplication pattern. Inside the same object there are several identical images.
        """
        _user = RightsBO.user_has_role(self.session, current_user_id, Role.APP_ADMINISTRATOR)
        orig_img = aliased(Image, name="orig")
        orig_file = aliased(ImageFile, name="orig_file")
        qry: Query = self.session.query(orig_img.file_name, orig_img.imgid, Image, ImageFile)  # Select what to delete
        qry = qry.join(ObjectHeader, ObjectHeader.objid == Image.objid).join(Acquisition).join(Sample).join(Project)
        # We consider that original image is the oldest one, so others have a superior ID
        qry = qry.join(orig_img, and_(orig_img.objid == Image.objid,
                                      orig_img.orig_file_name == Image.orig_file_name,
                                      orig_img.width == Image.width,
                                      orig_img.height == Image.height,
                                      orig_img.imgid < Image.imgid))
        # Must have a checksum, with the same state (sane)
        qry = qry.join(ImageFile, and_(ImageFile.path == Image.file_name,
                                       ImageFile.state == ImageFileStateEnum.OK.value))
        qry = qry.join(orig_file, and_(orig_file.path == orig_img.file_name,
                                       orig_file.state == ImageFileStateEnum.OK.value))
        # and the same value of course
        qry = qry.filter(and_(ImageFile.digest_type == orig_file.digest_type,
                              ImageFile.digest == orig_file.digest))
        qry = qry.filter(Project.projid == prj_id)
        qry = qry.order_by(Image.objid, orig_img.imgid, Image.imgid)
        qry = qry.limit(max_deletes)
        with CodeTimer("Dups same objs inside %d, query '%s':" % (prj_id, str(qry)), logger):
            to_do = [(orig_file_name, orig_img_id, an_image, an_image_file)
                     for orig_file_name, orig_img_id, an_image, an_image_file in qry.all()]
        ko_not_same = 0
        ko_except = 0
        # Prepare & start a remover thread that will run in // with DB queries
        remover = VaultRemover(self.link_src, logger).do_start()
        filecmp.clear_cache()
        deleted_imgids: Set[int] = set()
        for orig_file_name, orig_img_id, an_image, an_image_file in to_do:
            # The query returns multiple rows if there are more than 2 duplicates
            if orig_img_id in deleted_imgids:
                continue
            # Even if MD5s match, be paranoid and compare files
            orig_path = self.vault.sub_path(orig_file_name)
            dup_path = self.vault.sub_path(an_image.file_name)
            assert orig_path != dup_path
            try:
                same = filecmp.cmp(orig_path, dup_path, False)
            except Exception as exc:
                logger.info("Exception while comparing %s and %s: %s", orig_path, dup_path, str(exc))
                ko_except += 1
                continue
            if not same:
                ko_not_same += 1
                continue
            # Do the cleanup
            deleted_imgids.add(an_image.imgid)
            remover.add_files([an_image.file_name])
            self.session.delete(an_image)
            self.session.delete(an_image_file)
        # Wait for the files handled
        self.session.commit()
        remover.wait_for_done()
        return ("Dupl remover for %s dup images done but %d problems %d false file comp" %
                (len(deleted_imgids), ko_except, ko_not_same))
