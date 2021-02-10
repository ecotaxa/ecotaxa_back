# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Some functions around filesystem<->DB consistency in vault directory
#
import hashlib
from os.path import join
from typing import Optional

from API_operations.helpers.Service import Service
from BO.Project import ProjectIDT
from BO.Rights import RightsBO
from BO.User import UserIDT
from DB import ObjectHeader, Sample, Acquisition, Project, Role
from DB.Image import Image, ImageFile, ImageFileStateEnum
from DB.helpers.ORM import Query
from FS.Vault import Vault
from helpers.DynamicLogs import get_logger

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
        qry: Query = self.session.query(Image, ImageFile)
        if prj_id is not None:
            qry = qry.join(ObjectHeader).join(Acquisition).join(Sample).join(Project)
        qry = qry.outerjoin(ImageFile, Image.file_name == ImageFile.path)
        qry = qry.filter(ImageFile.path.is_(None))
        if prj_id is not None:
            qry = qry.filter(Project.projid == prj_id)
        qry = qry.limit(max_digests)
        cnt = 0
        for an_img, img_file in qry.all():
            cnt += 1
            if img_file is None:
                # No image_file line, add it
                img_file = ImageFile(path=an_img.file_name)
                self.session.add(img_file)
            img_file_path = self.vault.sub_path(an_img.file_name)
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
