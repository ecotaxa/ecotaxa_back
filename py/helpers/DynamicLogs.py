# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import logging


class DynamicFileHandler(logging.FileHandler):
    """
        A constant Logger to a switching file.
    """

    def __init__(self, filename, mode='a', encoding=None, delay=False):
        """
            Use the specified filename for streamed logging
        """
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)
        self.mode = mode
        self.encoding = encoding

    def switch_to(self, new_filename):
        """
            Move to another log file.
        """
        if self.stream:
            self.stream.close()
            # noinspection PyTypeChecker
            self.stream = None
        self.baseFilename = new_filename
        self.stream = self._open()


logging_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# TODO: It should be thread/request local
_the_handler = DynamicFileHandler("API_models.log")
_the_handler.setFormatter(logging.Formatter(logging_format))


def get_logger(name) -> logging.Logger:
    ret = logging.getLogger(name)
    ret.addHandler(_the_handler)
    ret.setLevel(logging.INFO)
    return ret


def switch_log_to_file(file_path: str):
    _the_handler.switch_to(file_path)
