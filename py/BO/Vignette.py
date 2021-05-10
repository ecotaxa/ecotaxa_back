# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from configparser import ConfigParser
from os.path import realpath, dirname, join
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont  # type: ignore

HERE = dirname(realpath(__file__))


class VignetteMaker(object):
    """
        Vignette factory, from original images and using a configuration file.

        AFTER ANY MODIFICATION HERE, please the corresponding UT with visual check of the output.
    """

    def __init__(self, cfg: ConfigParser, src_base: Path, target_filename: str):
        # Store all config. as the same file is used several times
        section = cfg['vignette']
        self.gamma = float(section['gamma'])
        self.scale = float(section['scale'])
        self.fontheight_px = int(section['fontheight_px'])
        self.scalebarsize_mm = float(section['scalebarsize_mm'])
        self.pixel_size = float(section['Pixel_Size'])
        # Invert image or not
        self.invert: bool = section['invert'].upper() == "Y"
        self.fontcolor = section['fontcolor']
        # 254 is nearly white, easier to detect programmatically
        self.bgcolor = "black" if self.fontcolor == "white" else 254
        self.footerheight_px = int(section['footerheight_px'])
        # Processing option, not relaed to image itself
        self.keep_original: bool = section.get('keeporiginal', 'n').lower() == 'y'
        # Read font from present directory
        font_file = join(HERE, 'resources', 'source-sans-pro-v9-latin-300.ttf')
        self.fnt = ImageFont.truetype(font_file, int(round(self.fontheight_px * 1.5)))
        # Where to find source images
        self.src_base = src_base
        # The common target file, erased at each call
        self.target_file = target_filename

    def must_keep_original(self):
        return self.keep_original

    def make_vignette(self, in_file_path: Path):
        pil_image = Image.open(self.src_base / in_file_path)
        np_img = np.array(pil_image)
        scalebarsize_px = int(round(self.scalebarsize_mm * 1000 / self.pixel_size, 0) * self.scale)
        minimgwidth = scalebarsize_px + 10
        if self.gamma != 1:
            np_img = np.power((np_img / 255), (1 / self.gamma)) * 255
            np_img = np_img.astype(np.uint8)
        if self.invert:
            np_img = 255 - np_img
        # Turn numpy array into an image, once calculations are done.
        pil_image = Image.fromarray(np_img)
        if self.scale != 1:
            pil_image = pil_image.resize((int(pil_image.size[0] * self.scale), int(pil_image.size[1] * self.scale)),
                                         Image.BICUBIC)
        # Generate scale band at the bottom of the image
        orig_img = pil_image
        # Generate a new image, larger for the scale band
        pil_image = Image.new(orig_img.mode,
                              (max([pil_image.size[0], minimgwidth]), pil_image.size[1] + self.footerheight_px),
                              self.bgcolor)
        # Paste the origin image at the top
        pil_image.paste(orig_img)
        height = pil_image.size[1]
        # Compose a drawing context for the scale
        draw = ImageDraw.Draw(pil_image)
        line_points = [(9, height - 4), (9 + int(round(scalebarsize_px)), height - 4)]
        # noinspection PyUnresolvedReferences
        line_points.insert(0, (line_points[0][0], line_points[0][1] + 2))
        line_points.append((line_points[2][0], line_points[2][1] + 2))
        # print(line_points)
        draw.line(line_points, fill=self.fontcolor)
        # draw.line(line_points[1:2] , fill=fontcolor)
        # fnt=draw.getfont()
        draw.text((10, height - 10 - self.fontheight_px), "%g mm" % self.scalebarsize_mm,
                  fill=self.fontcolor, font=self.fnt)
        # pil_image =pil_image.transform((pil_image.size[0],pil_image.size[1]+200),Image.EXTENT,
        # (0,0,pil_image.size[0],pil_image.size[1]),fill=1,fillcolor='red')
        # pil_image.save(dir+'\\testgamma_%s_%d.png'%(imgname,g))
        target_file = self.src_base.parent / self.target_file
        pil_image.save(target_file)
        # pil_image.show()
        return target_file
