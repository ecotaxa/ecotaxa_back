# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional

from PIL import Image as PIL_Image  # type: ignore
from PIL.Image import DecompressionBombError  # type: ignore

from DB.helpers.Bean import Bean
from FS.Vault import Vault


class ImageBO(object):
    """
        Holder for image operations.
    """

    @staticmethod
    def dimensions_and_resize(max_dim: int, vault: Vault, sub_path: str, image_to_write: Bean) -> Optional[str]:
        try:
            im = PIL_Image.open(vault.path_to(sub_path))
        except DecompressionBombError:
            return "Image too large: %s" % sub_path
        image_to_write.width = im.size[0]
        image_to_write.height = im.size[1]
        # Generate a thumbnail if image is too large
        if (im.size[0] > max_dim) or (im.size[1] > max_dim):
            im.thumbnail((max_dim, max_dim))
            if im.mode == 'P':
                # (8-bit pixels, mapped to any other mode using a color palette)
                # from https://pillow.readthedocs.io/en/latest/handbook/concepts.html#modes
                # Tested using a PNG with palette
                im = im.convert("RGB")
            thumb_relative_path, thumb_full_path = vault.thumbnail_paths(image_to_write.imgid)
            im.save(thumb_full_path)
            image_to_write.thumb_file_name = thumb_relative_path
            image_to_write.thumb_width = im.size[0]
            image_to_write.thumb_height = im.size[1]
        else:
            # Close the PIL image, when resized it was done during im.save
            # Otherwise there is a FD exhaustion on PyPy
            im.close()
            # Need empty fields for bulk insert
            image_to_write.thumb_file_name = None
            image_to_write.thumb_width = None
            image_to_write.thumb_height = None
        return None
