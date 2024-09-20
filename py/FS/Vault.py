# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import shutil
from pathlib import Path, PurePath
from typing import Set, Tuple


class Vault(object):
    """
    Class mirroring the image vault (filesystem)
    """

    def __init__(self, path: str):
        self.path: Path = Path(path)
        self.ok_subs: Set[str] = set()

    def ensure_exists(self, sub_directory: str) -> Path:
        """
            Ensure the subdirectory exists, i.e. create it, if not there, and return it.
            If another process asked for the same simultaneously then use it.
        :param sub_directory:
        """
        subdir: Path = self.path.joinpath(sub_directory)
        if sub_directory in self.ok_subs:
            return subdir
        try:
            if not subdir.exists():
                subdir.mkdir()
        except Exception as e:  # pragma: no cover
            # TODO: Multi-thread hammering test program for having a collision.
            if not subdir.exists():
                raise e
        self.ok_subs.add(sub_directory)
        return subdir

    @staticmethod
    def address_for_id(img_id: int) -> Tuple[str, str]:
        """
            Return the address, i.e. folder and unique identifier inside folder, for a given image ID.
        :param img_id:
        :return:
        """
        # Images are stored in folders of 10K images max
        return "%04d" % (img_id // 10000), "%04d" % (img_id % 10000)

    def store_image(self, img_file_path: Path, img_id: int, mini: bool = False) -> str:
        """
            Store, i.e. copy, an image having given path, into self, with given ID.
        :return: The image path, relative to root directory.
        """
        assert img_id is not None
        folder, ndx_in_folder = self.address_for_id(img_id)
        folder_path: PurePath = self.ensure_exists(folder)
        # Return the path relative to vault, keeping file suffix, e.g. .jpg or .png
        filename = "%s%s%s" % (
            ndx_in_folder,
            "_mini" if mini else "",
            img_file_path.suffix,
        )

        # Copy image file from source to vault (self)
        # TODO: Move if on same filesystem and unzip was done?
        # TODO: OS copy otherwise, 3x less time
        dest_img_path: str = folder_path.joinpath(filename).as_posix()
        shutil.copyfile(img_file_path.as_posix(), dest_img_path)
        # Return relative path, unix style
        sub_path = "%s/%s" % (folder, filename)
        return sub_path

    BASE_URL = "https://ecotaxa.obs-vlfr.fr/vault/%s"

    def ensure_there(self, img_maybe: Path, sub_path: str) -> bool:  # pragma:nocover
        """
        For devs, to ensure an image exists. If it doesn't, get it from main site.
        """
        is_there = img_maybe.exists()
        if not is_there:
            import requests
            import tempfile
            from os import unlink

            file_end = 9 if "_mini" in sub_path else 5 if ".jpeg" in sub_path else 4
            fout = tempfile.mktemp(suffix=sub_path[-file_end:])
            r = requests.get(self.BASE_URL % sub_path, stream=True)
            if r.status_code != 200:
                return False
            with open(fout, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            f.close()
            img_id = int(sub_path[:-file_end].replace("/", ""))
            self.store_image(Path(fout), img_id, file_end == 9)
            unlink(fout)
        return is_there

    def image_from_bkp(self, img_maybe: Path, sub_path: str) -> bool:  # pragma:nocover
        """
        For devs, get image from SIR_storage backup if not there.
        """
        is_there = img_maybe.exists()
        if not is_there:
            import os

            sub_dir = os.path.dirname(img_maybe)
            subdir: Path = self.path.joinpath(sub_dir)
            if sub_dir not in self.ok_subs:
                try:
                    # ssh with public key user@host
                    if not subdir.exists():
                        subdir.mkdir()
                        os.system(
                            "scp user@host:/SIR_Storage/Ecotaxa/vault/"
                            + os.path.dirname(sub_path)
                            + "/*"
                            + " "
                            + sub_dir
                        )
                except Exception as e:  # pragma: no cover
                    # TODO: Multi-thread hammering test program for having a collision.
                    if not subdir.exists():
                        raise e
                self.ok_subs.add(sub_dir)
        return is_there

    def image_path(self, img_sub_path: str) -> str:
        """
            Return absolute path to given referenced, i.e. assumed as _existing_, image,
             either plain or thumbnail, with given sub path e.g. '4567/345.png' or '5014/6481_mini.jpg'.
        :return:
        """
        full_path = self.path.joinpath(img_sub_path)
        # For devs. DO NOT COMMIT
        # self.ensure_there(full_path, img_sub_path)
        # self.image_from_bkp(full_path, img_sub_path)
        return full_path.as_posix()

    def thumbnail_paths(self, img_id: int) -> Tuple[str, str]:
        """
            Return relative and absolute paths to a thumbnail image.
            It is assumed that the main image was stored before, the common subdirectory must exist.
        :return:
        """
        folder, ndx_in_folder = self.address_for_id(img_id)
        # We force thumbnail format to JPEG
        sub_path = "%s/%s_mini.jpg" % (
            folder,
            ndx_in_folder,
        )  # TODO: Dup with Image.thumb_img_from_id_if_there
        return sub_path, self.path.joinpath(sub_path).as_posix()
