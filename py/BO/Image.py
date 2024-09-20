# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional

from PIL import Image as PIL_Image, PngImagePlugin  # type: ignore
from PIL.GifImagePlugin import GifImageFile  # type: ignore
from PIL.Image import DecompressionBombError  # type: ignore
from PIL.JpegImagePlugin import JpegImageFile  # type: ignore
from PIL.PngImagePlugin import PngImageFile  # type: ignore

from DB.helpers.Bean import Bean
from FS.Vault import Vault

SUPPORTED_FORMATS = {PngImageFile.format, JpegImageFile.format, GifImageFile.format}


class ImageBO(object):
    """
    Holder for image operations.
    """

    @staticmethod
    def validate_image(img_path: str):
        """
        Validate the (probable) image file at given path.
        """
        try:
            im = PIL_Image.open(img_path)
            im.load()
            img_format = im.format
            del im
            if img_format not in SUPPORTED_FORMATS:
                raise ImportError(
                    "Unsupported image format: %s, please convert to one of %s"
                    % (img_format, SUPPORTED_FORMATS)
                )
        except DecompressionBombError:
            raise ImportError("Image too large")
        except SyntaxError:  # From PIL/PngImagePlugin.py
            raise ImportError("Corrupted PNG")
        except Exception:
            raise

    @staticmethod
    def dimensions_and_resize(
        max_dim: int, vault: Vault, sub_path: str, image_to_write: Bean
    ) -> Optional[str]:
        """
        Get dimensions from given image, return a string with the error in case of issue.
        It is assumed that the image is valid, i.e. did not throw an exception in above validate()
        """
        im = PIL_Image.open(vault.image_path(sub_path))
        image_to_write.width = im.size[0]
        image_to_write.height = im.size[1]
        # Generate a thumbnail if image is too large
        if (im.size[0] > max_dim) or (im.size[1] > max_dim):
            if im.mode == "P" or im.mode[0] == "I":
                # (8-bit pixels, mapped to any other mode using a color palette)
                # from https://pillow.readthedocs.io/en/latest/handbook/concepts.html#modes
                # Tested using a PNG with palette
                im = im.convert("RGB")
            im.thumbnail((max_dim, max_dim))
            thumb_relative_path, thumb_full_path = vault.thumbnail_paths(
                image_to_write.imgid
            )
            im.save(thumb_full_path)  # TODO: Should be in Vault, no IO here
            image_to_write.thumb_width = im.size[0]
            image_to_write.thumb_height = im.size[1]
        else:
            # Close the PIL image, when resized it was done during im.save
            # Otherwise there is a FD exhaustion on PyPy
            im.close()
            # Need empty fields for bulk insert
            image_to_write.thumb_width = None
            image_to_write.thumb_height = None
        return None
