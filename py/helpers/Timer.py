# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# For timing portions of code
#
import time
from logging import Logger
from typing import Optional


class CodeTimer(object):
    """ """

    def __init__(self, msg: str, logger: Logger, limit: Optional[float] = None):
        self.msg = msg
        self.logger = logger
        self.start = None
        self.limit = limit

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start
        if exc_type is None:
            if self.limit is not None and elapsed < self.limit:
                return
            self.logger.info(self.msg + "%.02fms" % (elapsed * 1000))
