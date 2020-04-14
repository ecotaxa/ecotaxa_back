# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

import configparser
from os.path import dirname, realpath
from pathlib import Path

from BO.Vignette import VignetteMaker

DATA_DIR = Path(dirname(realpath(__file__))) / ".." / "data" / "vignette"

CONFIG = """
[vignette]
; gamma coefficiant of the gamma correction
gamma=1.2
; invert image (black => white) : Values Y/N case insensitive
invert=y
; size in millimeter of the scale bar
scalebarsize_mm=2.0
; load original image in Ecotaxa in adition of the computer vignette : Values Y/N case insensitive
keeporiginal=y
; color of the text in the footer (black or white), if white then background is black, else background is 254
fontcolor=black
; height of the text in the footer in pixel
fontheight_px=6
; height of the footer in pixel
footerheight_px=31
; scale factor to resize the image, 1 = No change , >1 increase size using bucubic method
scale=5
; pixel_size in micrometer will be added during sample generation, used to compute scalebar width
Pixel_Size=73
"""


def test_vignette1():
    """
        Just a check that the code does not error out.
    """
    config = configparser.ConfigParser()
    config.read_string(CONFIG)
    vignette = "0128_vig.png"
    maker = VignetteMaker(config, DATA_DIR, vignette)
    assert maker.must_keep_original()
    original = "0128.png"
    maker.make_vignette(original)
